//! tbf-scan binary entrypoint.

use std::process::ExitCode;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Instant;

use clap::Parser;
use futures::stream::{self, StreamExt};
use indicatif::{ProgressBar, ProgressStyle};
use tokio_util::sync::CancellationToken;
use tracing::{error, info, warn};

use tbf_scan::cli::Args;
use tbf_scan::db::{
    assert_leads_schema, count_no_website, ensure_schema, open_db, select_scan_targets, ScanFilters,
};
use tbf_scan::export::export_csv;
use tbf_scan::fetch::FetchStack;
use tbf_scan::url_norm::normalize_url;
use tbf_scan::writer::{self, WriterStats};
use tbf_scan::CHANNEL_CAPACITY;

#[tokio::main]
async fn main() -> ExitCode {
    match run().await {
        Ok(code) => code,
        Err(e) => {
            eprintln!("error: {e:#}");
            // invalid args / missing DB → 2; other runtime → 1
            let msg = format!("{e:#}").to_ascii_lowercase();
            if msg.contains("database not found")
                || msg.contains("missing required")
                || msg.contains("not found")
                || msg.contains("invalid")
            {
                ExitCode::from(2)
            } else {
                ExitCode::from(1)
            }
        }
    }
}

async fn run() -> anyhow::Result<ExitCode> {
    let args = Args::parse();

    let filter = if args.verbose {
        "tbf_scan=debug,info"
    } else {
        "tbf_scan=info,warn"
    };
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_target(false)
        .compact()
        .init();

    if args.concurrency == 0 {
        anyhow::bail!("invalid --concurrency: must be >= 1");
    }

    let conn = open_db(&args.db)?;
    assert_leads_schema(&conn)?;
    ensure_schema(&conn)?;

    let no_website = count_no_website(&conn)?;
    let filters = ScanFilters {
        city: args.city.clone(),
        zips: args.zips.clone(),
        industry: args.industry.clone(),
        limit: args.limit,
        resume: args.resume,
        max_age_days: args.max_age,
        force: args.force,
    };
    let targets = select_scan_targets(&conn, &filters)?;

    println!("tbf-scan — lightweight website lead scorer");
    println!("  db:            {}", args.db.display());
    println!("  no website:    {no_website}  (never scanned)");
    println!("  scan targets:  {}", targets.len());
    if args.resume && !args.force {
        println!("  resume:        on (max-age {}d)", args.max_age);
    }
    if args.force {
        println!("  force:         on");
    }

    if args.dry_run {
        println!("  mode:          dry-run (zero network calls)");
        let sample_n = targets.len().min(10);
        if sample_n == 0 {
            println!("  sample:        (none)");
        } else {
            println!("  sample (first {sample_n}):");
            for lead in targets.iter().take(sample_n) {
                let norm = normalize_url(&lead.website_url)
                    .unwrap_or_else(|e| format!("<invalid: {e}>"));
                println!(
                    "    id={}  city={}  zip={}  url={}  →  {}",
                    lead.id,
                    lead.city,
                    lead.zip_code.as_deref().unwrap_or("-"),
                    lead.website_url,
                    norm
                );
            }
        }
        println!("summary: dry-run complete | no website on file: {no_website}");
        return Ok(ExitCode::SUCCESS);
    }

    if targets.is_empty() {
        println!("summary: nothing to scan | no website on file: {no_website}");
        if let Some(path) = &args.export {
            let n = export_csv(&conn, path, args.min_score)?;
            println!("exported {n} rows → {}", path.display());
        }
        return Ok(ExitCode::SUCCESS);
    }

    drop(conn); // writer thread will re-open

    let cancel = CancellationToken::new();
    let cancel_bg = cancel.clone();
    tokio::spawn(async move {
        match tokio::signal::ctrl_c().await {
            Ok(()) => {
                eprintln!("\nCtrl-C — finishing in-flight writes…");
                cancel_bg.cancel();
            }
            Err(e) => warn!(error = %e, "ctrl_c handler failed"),
        }
    });

    let (tx, rx) = writer::channel(CHANNEL_CAPACITY);
    let writer_handle = {
        let db = args.db.clone();
        let cancel_w = cancel.clone();
        tokio::spawn(async move { writer::run_writer(db, rx, cancel_w).await })
    };

    let concurrency = args.concurrency;
    let verbose = args.verbose;
    let stack = Arc::new(FetchStack::new(concurrency)?);
    let total = targets.len() as u64;
    let pb = ProgressBar::new(total);
    pb.set_style(
        ProgressStyle::with_template(
            "{spinner:.green} [{elapsed_precise}] {bar:40.cyan/blue} {pos}/{len} ({per_sec}) ETA {eta} | unreachable {msg}",
        )?
        .progress_chars("##-"),
    );
    let unreachable = Arc::new(AtomicU64::new(0));
    pb.set_message("0");

    let start = Instant::now();
    let cancel_scan = cancel.clone();

    stream::iter(targets)
        .map(|lead| {
            let stack = Arc::clone(&stack);
            let tx = tx.clone();
            let pb = pb.clone();
            let unreachable = Arc::clone(&unreachable);
            let cancel_scan = cancel_scan.clone();
            async move {
                if cancel_scan.is_cancelled() {
                    return;
                }
                let url = match normalize_url(&lead.website_url) {
                    Ok(u) => u,
                    Err(e) => {
                        let outcome = tbf_scan::fetch::FetchOutcome {
                            lead_id: lead.id,
                            url_attempted: lead.website_url.clone(),
                            final_url: None,
                            reachable: false,
                            http_status: None,
                            ttfb_ms: None,
                            total_ms: None,
                            bytes: None,
                            is_https: None,
                            tls_ok: None,
                            error_kind: "parse".into(),
                            score: None,
                            signals_json: serde_json::json!({
                                "error_kind": "parse",
                                "url_error": e.to_string(),
                            })
                            .to_string(),
                        };
                        let _ = tx.send(outcome).await;
                        pb.inc(1);
                        return;
                    }
                };

                let outcome = stack
                    .scan_lead(lead.id, &url, lead.zip_code.as_deref())
                    .await;

                if matches!(
                    outcome.error_kind.as_str(),
                    "dns" | "timeout" | "refused" | "redirect_loop"
                ) {
                    let n = unreachable.fetch_add(1, Ordering::Relaxed) + 1;
                    pb.set_message(n.to_string());
                }

                if verbose {
                    info!(
                        lead_id = lead.id,
                        score = ?outcome.score,
                        kind = %outcome.error_kind,
                        url = %url,
                        "scanned"
                    );
                }

                if tx.send(outcome).await.is_err() {
                    // writer gone
                }
                pb.inc(1);
            }
        })
        .buffer_unordered(concurrency)
        .for_each(|_| async {})
        .await;

    drop(tx); // close channel → writer drains and exits
    pb.finish_and_clear();

    let stats: WriterStats = match writer_handle.await {
        Ok(Ok(s)) => s,
        Ok(Err(e)) => {
            error!(error = %e, "writer failed");
            return Err(e);
        }
        Err(e) => anyhow::bail!("writer join: {e}"),
    };

    let elapsed = start.elapsed().as_secs_f64().max(0.001);
    let rate = stats.written as f64 / elapsed;

    println!(
        "summary: scanned={} written={} unreachable={} robots={} write_errors={} rate={:.1}/s elapsed={:.1}s",
        total,
        stats.written,
        stats.unreachable,
        stats.robots_blocked,
        stats.errors,
        rate,
        elapsed
    );
    println!("  no website on file: {no_website}");

    // Re-open for export / min-score listing
    let conn = open_db(&args.db)?;
    if let Some(path) = &args.export {
        let n = export_csv(&conn, path, args.min_score)?;
        println!("exported {n} rows → {}", path.display());
    } else if let Some(min) = args.min_score {
        println!("leads with score >= {min}:");
        let mut stmt = conn.prepare(
            r#"
            SELECT l.id, l.name, l.city, s.score, l.website_url
            FROM leads l
            JOIN site_scans s ON s.lead_id = l.id
            WHERE s.id = (
              SELECT id FROM site_scans WHERE lead_id = l.id
              ORDER BY scanned_at DESC LIMIT 1
            )
            AND s.score IS NOT NULL AND s.score >= ?1
            ORDER BY s.score DESC
            LIMIT 50
            "#,
        )?;
        let rows = stmt.query_map(rusqlite::params![min], |r| {
            Ok((
                r.get::<_, i64>(0)?,
                r.get::<_, String>(1)?,
                r.get::<_, String>(2)?,
                r.get::<_, i32>(3)?,
                r.get::<_, String>(4)?,
            ))
        })?;
        for row in rows {
            let (id, name, city, score, url) = row?;
            println!("  [{score:>3}] id={id} {name} ({city}) {url}");
        }
    }

    Ok(ExitCode::SUCCESS)
}
