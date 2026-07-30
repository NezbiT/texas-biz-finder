//! Integration: schema create + dry-run style SELECT with zero network.

use std::path::PathBuf;

use rusqlite::Connection;
use tbf_scan::db::{
    assert_leads_schema, count_no_website, ensure_schema, insert_scan, select_scan_targets,
    LeadRow, ScanFilters, SiteScanInsert,
};
use tbf_scan::url_norm::normalize_url;

fn fixture_db() -> (tempfile::TempDir, PathBuf) {
    let dir = tempfile::tempdir().expect("tempdir");
    let path = dir.path().join("test.db");
    let conn = Connection::open(&path).unwrap();
    conn.execute_batch(
        r#"
        CREATE TABLE leads (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            zip_code TEXT,
            industry TEXT,
            website_url TEXT,
            has_website INTEGER NOT NULL DEFAULT 0
        );
        INSERT INTO leads (id, external_id, name, city, zip_code, industry, website_url, has_website)
        VALUES
          (1, 'a', 'Alpha Bakery', 'Austin', '78702', 'Food', 'https://alpha.example/?utm_source=x', 1),
          (2, 'b', 'Beta Shop', 'El Paso', '79901', 'Retail', NULL, 0),
          (3, 'c', 'Gamma LLC', 'Houston', '77002', 'Services', '  ', 0),
          (4, 'd', 'Delta Co', 'Dallas', '75211', 'Services', 'delta.example', 1);
        "#,
    )
    .unwrap();
    (dir, path)
}

#[test]
fn schema_and_target_select() {
    let (_dir, path) = fixture_db();
    let conn = Connection::open(&path).unwrap();
    assert_leads_schema(&conn).unwrap();
    ensure_schema(&conn).unwrap();

    let no_web = count_no_website(&conn).unwrap();
    assert_eq!(no_web, 2); // NULL + blank

    let targets = select_scan_targets(&conn, &ScanFilters::default()).unwrap();
    assert_eq!(targets.len(), 2);
    assert_eq!(targets[0].id, 1);
    assert_eq!(targets[1].id, 4);

    let norm = normalize_url(&targets[0].website_url).unwrap();
    assert_eq!(norm, "https://alpha.example/");
    let norm2 = normalize_url(&targets[1].website_url).unwrap();
    assert_eq!(norm2, "https://delta.example/");
}

#[test]
fn resume_skips_recent_scans() {
    let (_dir, path) = fixture_db();
    let conn = Connection::open(&path).unwrap();
    ensure_schema(&conn).unwrap();

    insert_scan(
        &conn,
        &SiteScanInsert {
            lead_id: 1,
            url_attempted: "https://alpha.example/".into(),
            final_url: Some("https://alpha.example/".into()),
            scanned_at: chrono::Utc::now().to_rfc3339(),
            reachable: true,
            http_status: Some(200),
            ttfb_ms: Some(10),
            total_ms: Some(20),
            bytes: Some(100),
            is_https: Some(true),
            tls_ok: Some(true),
            error_kind: "none".into(),
            score: Some(12),
            signals_json: "{}".into(),
        },
    )
    .unwrap();

    let filters = ScanFilters {
        resume: true,
        max_age_days: 30,
        force: false,
        ..Default::default()
    };
    let targets = select_scan_targets(&conn, &filters).unwrap();
    assert_eq!(targets.len(), 1);
    assert_eq!(targets[0].id, 4);

    let force = ScanFilters {
        resume: true,
        force: true,
        ..Default::default()
    };
    let all = select_scan_targets(&conn, &force).unwrap();
    assert_eq!(all.len(), 2);
}

#[test]
fn only_creates_site_scans_objects() {
    let (_dir, path) = fixture_db();
    let conn = Connection::open(&path).unwrap();
    ensure_schema(&conn).unwrap();
    ensure_schema(&conn).unwrap(); // idempotent

    let names: Vec<String> = conn
        .prepare(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view','index') ORDER BY 1",
        )
        .unwrap()
        .query_map([], |r| r.get(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect();

    assert!(names.iter().any(|n| n == "site_scans"));
    assert!(names.iter().any(|n| n == "v_top_leads"));
    assert!(names.iter().any(|n| n == "idx_site_scans_lead"));
    assert!(names.iter().any(|n| n == "idx_site_scans_score"));
    // leads untouched as table name still present
    assert!(names.iter().any(|n| n == "leads"));
}

#[test]
fn city_filter() {
    let (_dir, path) = fixture_db();
    let conn = Connection::open(&path).unwrap();
    let filters = ScanFilters {
        city: Some("austin".into()),
        ..Default::default()
    };
    let rows: Vec<LeadRow> = select_scan_targets(&conn, &filters).unwrap();
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0].name, "Alpha Bakery");
}
