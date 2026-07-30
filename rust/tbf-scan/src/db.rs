//! SQLite access: read-only leads queries + create-only site_scans schema.

use std::path::Path;

use anyhow::{bail, Context, Result};
use rusqlite::{params, Connection, OptionalExtension};

/// Row selected for scanning from real `leads` schema.
#[derive(Debug, Clone)]
pub struct LeadRow {
    pub id: i64,
    pub name: String,
    pub city: String,
    pub zip_code: Option<String>,
    pub industry: Option<String>,
    pub website_url: String,
}

#[derive(Debug, Clone, Default)]
pub struct ScanFilters {
    pub city: Option<String>,
    pub zips: Vec<String>,
    pub industry: Option<String>,
    pub limit: Option<usize>,
    pub resume: bool,
    pub max_age_days: u32,
    pub force: bool,
}

/// Open SQLite with sane defaults for concurrent readers + one writer.
pub fn open_db(path: &Path) -> Result<Connection> {
    if !path.exists() {
        bail!("database not found: {}", path.display());
    }
    let conn = Connection::open(path)
        .with_context(|| format!("open sqlite {}", path.display()))?;
    conn.pragma_update(None, "journal_mode", "WAL")?;
    conn.pragma_update(None, "synchronous", "NORMAL")?;
    conn.pragma_update(None, "busy_timeout", 5000i64)?;
    conn.pragma_update(None, "foreign_keys", "ON")?;
    Ok(conn)
}

/// Create only the objects allowed by the hard boundary.
pub fn ensure_schema(conn: &Connection) -> Result<()> {
    conn.execute_batch(
        r#"
        CREATE TABLE IF NOT EXISTS site_scans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id         INTEGER NOT NULL,
            url_attempted   TEXT    NOT NULL,
            final_url       TEXT,
            scanned_at      TEXT    NOT NULL,
            reachable       INTEGER NOT NULL DEFAULT 0,
            http_status     INTEGER,
            ttfb_ms         INTEGER,
            total_ms        INTEGER,
            bytes           INTEGER,
            is_https        INTEGER,
            tls_ok          INTEGER,
            error_kind      TEXT,
            score           INTEGER,
            signals_json    TEXT    NOT NULL,
            UNIQUE(lead_id, scanned_at)
        );

        CREATE INDEX IF NOT EXISTS idx_site_scans_lead  ON site_scans(lead_id);
        CREATE INDEX IF NOT EXISTS idx_site_scans_score ON site_scans(score DESC)
            WHERE score IS NOT NULL;

        CREATE VIEW IF NOT EXISTS v_top_leads AS
        SELECT
          l.id, l.name, l.city, l.zip_code, l.industry, l.website_url,
          s.score, s.final_url, s.error_kind, s.scanned_at, s.signals_json
        FROM leads l
        JOIN site_scans s ON s.lead_id = l.id
        WHERE s.id = (
          SELECT id FROM site_scans
          WHERE lead_id = l.id
          ORDER BY scanned_at DESC
          LIMIT 1
        )
        ORDER BY s.score DESC NULLS LAST;
        "#,
    )?;
    Ok(())
}

/// Count rows with no usable website URL (never scanned).
pub fn count_no_website(conn: &Connection) -> Result<i64> {
    let n: i64 = conn.query_row(
        r#"
        SELECT COUNT(*) FROM leads
        WHERE website_url IS NULL OR trim(website_url) = ''
        "#,
        [],
        |r| r.get(0),
    )?;
    Ok(n)
}

/// Verify `leads` has the columns we rely on (fail fast on drift).
pub fn assert_leads_schema(conn: &Connection) -> Result<()> {
    let mut stmt = conn.prepare("PRAGMA table_info(leads)")?;
    let cols: Vec<String> = stmt
        .query_map([], |r| r.get::<_, String>(1))?
        .collect::<std::result::Result<Vec<_>, _>>()?;

    if cols.is_empty() {
        bail!("table `leads` not found in database");
    }

    for required in [
        "id",
        "name",
        "city",
        "zip_code",
        "industry",
        "website_url",
        "has_website",
    ] {
        if !cols.iter().any(|c| c == required) {
            bail!("leads schema missing required column `{required}` (found: {cols:?})");
        }
    }
    Ok(())
}

/// Select scan targets from real `leads` columns.
pub fn select_scan_targets(conn: &Connection, filters: &ScanFilters) -> Result<Vec<LeadRow>> {
    let mut sql = String::from(
        r#"
        SELECT l.id, l.name, l.city, l.zip_code, l.industry, l.website_url
        FROM leads l
        WHERE l.website_url IS NOT NULL
          AND length(trim(l.website_url)) > 0
        "#,
    );
    let mut binds: Vec<Box<dyn rusqlite::types::ToSql>> = Vec::new();

    if let Some(city) = &filters.city {
        sql.push_str(" AND lower(l.city) = lower(?)");
        binds.push(Box::new(city.clone()));
    }
    if !filters.zips.is_empty() {
        let placeholders = filters
            .zips
            .iter()
            .map(|_| "?")
            .collect::<Vec<_>>()
            .join(", ");
        sql.push_str(&format!(" AND l.zip_code IN ({placeholders})"));
        for z in &filters.zips {
            binds.push(Box::new(z.clone()));
        }
    }
    if let Some(industry) = &filters.industry {
        sql.push_str(" AND lower(coalesce(l.industry, '')) LIKE '%' || lower(?) || '%'");
        binds.push(Box::new(industry.clone()));
    }

    // Resume: skip leads whose latest scan is within max-age days (unless --force).
    // scanned_at is RFC3339; normalize to SQLite datetime for comparison.
    if filters.resume && !filters.force {
        sql.push_str(
            r#"
            AND NOT EXISTS (
              SELECT 1 FROM site_scans s
              WHERE s.lead_id = l.id
                AND datetime(substr(replace(s.scanned_at, 'T', ' '), 1, 19))
                    >= datetime('now', ?)
            )
            "#,
        );
        let age = format!("-{} days", filters.max_age_days);
        binds.push(Box::new(age));
    }

    sql.push_str(" ORDER BY l.id ASC");

    if let Some(limit) = filters.limit {
        sql.push_str(" LIMIT ?");
        binds.push(Box::new(limit as i64));
    }

    let mut stmt = conn.prepare(&sql)?;
    let params_ref: Vec<&dyn rusqlite::types::ToSql> = binds.iter().map(|b| b.as_ref()).collect();
    let rows = stmt.query_map(params_ref.as_slice(), |r| {
        Ok(LeadRow {
            id: r.get(0)?,
            name: r.get(1)?,
            city: r.get(2)?,
            zip_code: r.get(3)?,
            industry: r.get(4)?,
            website_url: r.get(5)?,
        })
    })?;

    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}

/// Insert one completed scan (writer path).
#[derive(Debug, Clone)]
pub struct SiteScanInsert {
    pub lead_id: i64,
    pub url_attempted: String,
    pub final_url: Option<String>,
    pub scanned_at: String,
    pub reachable: bool,
    pub http_status: Option<i32>,
    pub ttfb_ms: Option<i64>,
    pub total_ms: Option<i64>,
    pub bytes: Option<i64>,
    pub is_https: Option<bool>,
    pub tls_ok: Option<bool>,
    pub error_kind: String,
    pub score: Option<i32>,
    pub signals_json: String,
}

pub fn insert_scan(conn: &Connection, row: &SiteScanInsert) -> Result<i64> {
    conn.execute(
        r#"
        INSERT INTO site_scans (
            lead_id, url_attempted, final_url, scanned_at, reachable,
            http_status, ttfb_ms, total_ms, bytes, is_https, tls_ok,
            error_kind, score, signals_json
        ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)
        "#,
        params![
            row.lead_id,
            row.url_attempted,
            row.final_url,
            row.scanned_at,
            if row.reachable { 1 } else { 0 },
            row.http_status,
            row.ttfb_ms,
            row.total_ms,
            row.bytes,
            row.is_https.map(|v| if v { 1 } else { 0 }),
            row.tls_ok.map(|v| if v { 1 } else { 0 }),
            row.error_kind,
            row.score,
            row.signals_json,
        ],
    )?;
    Ok(conn.last_insert_rowid())
}

/// Latest score for a lead (for export/print filtering).
pub fn latest_scan_score(conn: &Connection, lead_id: i64) -> Result<Option<i32>> {
    let score: Option<i32> = conn
        .query_row(
            r#"
            SELECT score FROM site_scans
            WHERE lead_id = ?1
            ORDER BY scanned_at DESC
            LIMIT 1
            "#,
            params![lead_id],
            |r| r.get(0),
        )
        .optional()?;
    Ok(score)
}
