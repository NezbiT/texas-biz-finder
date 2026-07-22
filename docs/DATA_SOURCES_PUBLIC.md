# Public APIs & open data for TxBizFinder Intelligence

Keys marked **free** usually require registration only.

## Flood / weather / hydro

| Source | Auth | Use |
|--------|------|-----|
| [NWS api.weather.gov](https://www.weather.gov/documentation/services-web-api) | Free, User-Agent | Active alerts TX (live in FloodGuard) |
| [FEMA NFHL ArcGIS](https://hazards.fema.gov/femaportal/wps/portal/NFHLWMS) | Free | Official flood hazard zones (Pro tier) |
| [OpenFEMA](https://www.fema.gov/about/openfema/data-sets) | Free | NFIP claims, disaster declarations |
| [USGS NWIS](https://waterservices.usgs.gov/) | Free | Stream gauges |
| [NOAA CO-OPS](https://tidesandcurrents.noaa.gov/api/) | Free | Coastal water levels (ChannelWatch live) |
| [Open-Meteo](https://open-meteo.com/) | Free | Weather + air quality (ChannelWatch) |

## Air / emissions / energy

| Source | Auth | Use |
|--------|------|-----|
| [EPA AirNow](https://docs.airnowapi.org/) | Free key | AQI |
| [OpenAQ](https://openaq.org/) | Free key | Ambient monitors |
| [EPA CAMPD](https://www.epa.gov/power-sector/cam-api-portal) | Free key | Power plant CEMS |
| [EIA Open Data](https://www.eia.gov/opendata/) | Free key | Generation, demand, fuels |
| [EPA GHGRP](https://www.epa.gov/ghgreporting) | Bulk download | Facility GHG |
| [EPA eGRID](https://www.epa.gov/egrid) | Bulk | Emission rates |
| [EPA TRI](https://www.epa.gov/toxics-release-inventory-tri-program) | Bulk / Envirofacts | Facility releases |
| [TCEQ open data / GIS](https://www.tceq.texas.gov/gis) | Free | TX inventories, layers |
| ERCOT public | Varies | Grid conditions (terms) |

## Permits / business

| Source | Auth | Use |
|--------|------|-----|
| Houston Permitting Center weekly xlsx | Scrape | PermitRadar primary |
| [Austin SODA](https://data.austintexas.gov/) | Free (app token optional) | Permits |
| [Dallas Open Data](https://www.dallasopendata.com/) | Free | Permits |
| [San Antonio CKAN](https://data.sanantonio.gov/) | Free | Permits |
| [data.texas.gov franchise tax](https://data.texas.gov/) | Free | BizFinder universe |
| Mixed beverage receipts (TABC) | Free Socrata | Alcohol sales join |
| [US Census geocoder](https://geocoding.geo.census.gov/) | Free | Batch geocode |
| Zippopotam / Census | Free | ZIP → lat/lon |

## Implementation order (recommended)

1. **NWS + Open-Meteo + NOAA** — zero cost live weather risk (done partially)  
2. **EIA + AirNow free keys** — energy + AQI credibility  
3. **FEMA NFHL WMS/FeatureServer** — insurer-grade flood polygons  
4. **OpenFEMA NFIP** — claims density by ZIP (actuarial storytelling)  
5. **CAMPD + GHGRP bulk** — industrial underwriting overlays  
6. **Unified `api.txbizfinder.com` gateway** — one key, tiered rate limits  

## Legal

Always label non-authoritative layers. Flood/insurance decisions require official FEMA products and licensed professionals.
