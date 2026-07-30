//! Single dedicated writer task that owns the SQLite connection.

use std::path::PathBuf;
use std::time::Duration;

use anyhow::Result;
use chrono::Utc;
use tokio::sync::mpsc;
use tokio_util::sync::CancellationToken;
use tracing::{error, info};

use crate::db::{ensure_schema, insert_scan, open_db, SiteScanInsert};
use crate::fetch::FetchOutcome;

pub type ScanTx = mpsc::Sender<FetchOutcome>;
pub type ScanRx = mpsc::Receiver<FetchOutcome>;

pub fn channel(capacity: usize) -> (ScanTx, ScanRx) {
    mpsc::channel(capacity)
}

/// Run the writer until the channel closes or cancel is triggered after drain.
pub async fn run_writer(
    db_path: PathBuf,
    mut rx: ScanRx,
    cancel: CancellationToken,
) -> Result<WriterStats> {
    // rusqlite Connection is !Send on some configs — run all DB work on a blocking thread
    // via a dedicated OS thread with a channel of inserts.
    let (job_tx, job_rx) = std::sync::mpsc::sync_channel::<WriterJob>(64);
    let db_path_clone = db_path.clone();
    let handle = std::thread::spawn(move || -> Result<WriterStats> {
        let conn = open_db(&db_path_clone)?;
        ensure_schema(&conn)?;
        let mut stats = WriterStats::default();
        while let Ok(job) = job_rx.recv() {
            match job {
                WriterJob::Insert(outcome) => {
                    let scanned_at = Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true);
                    let row = SiteScanInsert {
                        lead_id: outcome.lead_id,
                        url_attempted: outcome.url_attempted,
                        final_url: outcome.final_url,
                        scanned_at,
                        reachable: outcome.reachable,
                        http_status: outcome.http_status,
                        ttfb_ms: outcome.ttfb_ms,
                        total_ms: outcome.total_ms,
                        bytes: outcome.bytes,
                        is_https: outcome.is_https,
                        tls_ok: outcome.tls_ok,
                        error_kind: outcome.error_kind,
                        score: outcome.score,
                        signals_json: outcome.signals_json,
                    };
                    match insert_scan(&conn, &row) {
                        Ok(_) => {
                            stats.written += 1;
                            if !row.reachable {
                                stats.unreachable += 1;
                            }
                            if row.error_kind == "robots" {
                                stats.robots_blocked += 1;
                            }
                        }
                        Err(e) => {
                            stats.errors += 1;
                            error!(error = %e, lead_id = row.lead_id, "insert failed");
                        }
                    }
                }
                WriterJob::Shutdown => break,
            }
        }
        // Ensure durability
        let _ = conn.execute_batch("PRAGMA wal_checkpoint(TRUNCATE);");
        Ok(stats)
    });

    loop {
        tokio::select! {
            biased;
            _ = cancel.cancelled() => {
                // Drain remaining already-received results briefly
                info!("writer: cancel observed — draining in-flight results");
                while let Ok(outcome) = rx.try_recv() {
                    let _ = job_tx.send(WriterJob::Insert(outcome));
                }
                // small grace for channel producers
                tokio::time::sleep(Duration::from_millis(50)).await;
                while let Ok(outcome) = rx.try_recv() {
                    let _ = job_tx.send(WriterJob::Insert(outcome));
                }
                break;
            }
            maybe = rx.recv() => {
                match maybe {
                    Some(outcome) => {
                        if job_tx.send(WriterJob::Insert(outcome)).is_err() {
                            break;
                        }
                    }
                    None => break,
                }
            }
        }
    }

    let _ = job_tx.send(WriterJob::Shutdown);
    match handle.join() {
        Ok(res) => res,
        Err(_) => anyhow::bail!("writer thread panicked"),
    }
}

enum WriterJob {
    Insert(FetchOutcome),
    Shutdown,
}

#[derive(Debug, Default, Clone)]
pub struct WriterStats {
    pub written: u64,
    pub unreachable: u64,
    pub robots_blocked: u64,
    pub errors: u64,
}
