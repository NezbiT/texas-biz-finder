//! CSV export of top scored leads (pitch-doctor oriented columns).

use std::path::Path;

use anyhow::{Context, Result};
use rusqlite::Connection;

/// Export latest scans joined with lead identity columns.
pub fn export_csv(conn: &Connection, path: &Path, min_score: Option<i32>) -> Result<usize> {
    let mut sql = String::from(
        r#"
        SELECT
          l.id, l.name, l.city, l.zip_code, l.industry, l.website_url,
          s.score, s.final_url, s.error_kind, s.scanned_at, s.signals_json,
          s.reachable, s.http_status, s.ttfb_ms, s.total_ms
        FROM leads l
        JOIN site_scans s ON s.lead_id = l.id
        WHERE s.id = (
          SELECT id FROM site_scans
          WHERE lead_id = l.id
          ORDER BY scanned_at DESC
          LIMIT 1
        )
        "#,
    );
    if min_score.is_some() {
        sql.push_str(" AND s.score IS NOT NULL AND s.score >= ?1");
    }
    sql.push_str(" ORDER BY s.score DESC NULLS LAST, l.id ASC");

    let mut stmt = conn.prepare(&sql)?;
    let mut rows = if let Some(min) = min_score {
        stmt.query(rusqlite::params![min])?
    } else {
        stmt.query([])?
    };

    let mut wtr = csv::Writer::from_path(path)
        .with_context(|| format!("create csv {}", path.display()))?;
    wtr.write_record([
        "id",
        "name",
        "city",
        "zip_code",
        "industry",
        "website_url",
        "score",
        "final_url",
        "error_kind",
        "scanned_at",
        "reachable",
        "http_status",
        "ttfb_ms",
        "total_ms",
        "signals_json",
    ])?;

    let mut count = 0usize;
    while let Some(row) = rows.next()? {
        let id: i64 = row.get(0)?;
        let name: String = row.get(1)?;
        let city: String = row.get(2)?;
        let zip: Option<String> = row.get(3)?;
        let industry: Option<String> = row.get(4)?;
        let website_url: Option<String> = row.get(5)?;
        let score: Option<i32> = row.get(6)?;
        let final_url: Option<String> = row.get(7)?;
        let error_kind: Option<String> = row.get(8)?;
        let scanned_at: String = row.get(9)?;
        let signals_json: String = row.get(10)?;
        let reachable: i32 = row.get(11)?;
        let http_status: Option<i32> = row.get(12)?;
        let ttfb_ms: Option<i64> = row.get(13)?;
        let total_ms: Option<i64> = row.get(14)?;

        wtr.write_record([
            id.to_string(),
            name,
            city,
            zip.unwrap_or_default(),
            industry.unwrap_or_default(),
            website_url.unwrap_or_default(),
            score.map(|s| s.to_string()).unwrap_or_default(),
            final_url.unwrap_or_default(),
            error_kind.unwrap_or_default(),
            scanned_at,
            reachable.to_string(),
            http_status.map(|s| s.to_string()).unwrap_or_default(),
            ttfb_ms.map(|s| s.to_string()).unwrap_or_default(),
            total_ms.map(|s| s.to_string()).unwrap_or_default(),
            signals_json,
        ])?;
        count += 1;
    }
    wtr.flush()?;
    Ok(count)
}
