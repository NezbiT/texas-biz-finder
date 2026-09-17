# Railway — FastAPI + DuckDB persistente

Este servicio usa el `Dockerfile` y `railway.toml` de la raíz. DuckDB ya es
una dependencia de producción (`duckdb` está en `pyproject.toml` y
`requirements.txt`); lo que no viaja con GitHub es la base generada, porque
`data/` está correctamente ignorado y ocupa aproximadamente 1.2 GB localmente.

## 1. Servicio y volumen

En Railway crea (o abre) el servicio conectado a este repositorio y verifica
que su **Root Directory** sea la raíz del repositorio. Genera un dominio público.

Adjunta un volumen al mismo servicio con:

```
Mount path: /app/data
```

Reserva al menos **5 GB**. El pipeline conserva los dos CSV de origen mientras
materializa `processed/texas_leads.duckdb`; con el volumen lleno el proceso se
interrumpe. El volumen se monta en runtime, así que nunca pongas la ingesta en
el build ni en un pre-deploy command.

Como la imagen usa el usuario `appuser` y Railway monta los volúmenes como
root, añade `RAILWAY_RUN_UID=0` a las variables del servicio. Esto permite que
la descarga y SQLite escriban en el volumen.

## 2. Variables del backend

En **Variables → Raw Editor**, define lo siguiente. Sustituye el valor del
secreto por uno largo y aleatorio; no lo confirmes en Git.

```
APP_ENV=production
ADMIN_API_KEY=<secreto-largo-aleatorio>
DATA_BACKEND=csv
DATABASE_URL=sqlite:////app/data/texasbizfinder.db
FRANCHISE_CSV_PATH=/app/data/raw/texas_franchise_taxpayers.csv
BEVERAGE_CSV_PATH=/app/data/raw/mixed_beverage_receipts.csv
PROCESSED_CSV_PATH=/app/data/processed/texas_leads_processed.csv
PROCESSED_DUCKDB_PATH=/app/data/processed/texas_leads.duckdb
ENABLE_WEBSITE_RESEARCH=false
UVICORN_WORKERS=1
DUCKDB_THREADS=1
DUCKDB_MEMORY_LIMIT=1GB
RAILWAY_RUN_UID=0
CORS_ORIGINS=["https://www.txbizfinder.com","https://txbizfinder.com","https://YOUR-VERCEL-PROJECT.vercel.app"]
```

No definas `PORT`: Railway lo inyecta y el `Dockerfile` ya escucha en él. Tras
el deploy, `https://TU-API.up.railway.app/health` debe responder HTTP 200. Antes
de la carga masiva puede decir `dataReady: false`; eso es esperado y las
búsquedas devuelven 503 en lugar de datos incompletos.

## 3. Cargar DuckDB en el volumen

Hay dos opciones. La más rápida si ya tienes los archivos locales generados es
subir **solo** los dos artefactos que la API necesita al volumen con Railway CLI:

```
railway volume files upload data/processed/texas_leads.duckdb /processed/texas_leads.duckdb
railway volume files upload data/processed/bulk_stats.json /processed/bulk_stats.json
```

Selecciona primero el proyecto, entorno, servicio y volumen correctos en la
CLI. La ruta remota es relativa al volumen `/app/data`, por eso `/processed/...`
termina en `/app/data/processed/...` dentro del contenedor.

Si prefieres descargar datos nuevos directamente desde Railway, abre una shell
del servicio y corre:

```
python -m scripts.bulk_pipeline all
```

El comando descarga ambos CSV y genera la DuckDB. Mantén un solo worker y no
reinicies el servicio mientras está corriendo. Comprueba el resultado:

```
curl -fsS https://TU-API.up.railway.app/health
```

Debe mostrar `"dataBackend":"csv"` y `"dataReady":true`.

## 4. Enlazar Vercel

En el proyecto Vercel cuyo **Root Directory** es `frontend-v2`, define para
Production (y Preview si lo necesitas):

```
NUXT_API_PROXY_URL=https://TU-API.up.railway.app
NUXT_PUBLIC_ADMIN_API_KEY=<mismo ADMIN_API_KEY>
```

`NUXT_API_PROXY_URL` se evalúa durante el build de Nuxt, por lo que hay que
hacer un redeploy de Vercel después de guardarla. No uses
`NUXT_PUBLIC_API_BASE_URL` para esta arquitectura: déjalo vacío para que el
navegador llame al mismo origen `/api` y Nuxt lo reenvíe a Railway.

Validación final desde el navegador: abre `https://TU-VERCEL.vercel.app/api/leads/stats`;
debe devolver JSON, no HTML ni 404. Si devuelve 401, la clave pública de Vercel
no coincide con `ADMIN_API_KEY`; si devuelve 503, aún falta DuckDB o las rutas
del volumen no coinciden.
