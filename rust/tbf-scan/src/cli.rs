use std::path::PathBuf;

use clap::Parser;

use crate::DEFAULT_CONCURRENCY;

/// Lightweight website lead scorer for TX BizFinder.
#[derive(Debug, Clone, Parser)]
#[command(
    name = "tbf-scan",
    version,
    about = "Fast, polite, resumable first-pass scorer of leads.website_url"
)]
pub struct Args {
    /// Path to the SQLite database (must contain `leads`).
    #[arg(long)]
    pub db: PathBuf,

    /// Maximum number of leads to scan.
    #[arg(long)]
    pub limit: Option<usize>,

    /// Global concurrent fetchers (default 64).
    #[arg(long, default_value_t = DEFAULT_CONCURRENCY)]
    pub concurrency: usize,

    /// Skip leads whose latest scan is newer than --max-age days.
    #[arg(long, default_value_t = false)]
    pub resume: bool,

    /// Max age in days for resume skip (default 30).
    #[arg(long, default_value_t = 30)]
    pub max_age: u32,

    /// Re-scan even if a recent scan exists (ignores --resume / --max-age).
    #[arg(long, default_value_t = false)]
    pub force: bool,

    /// Filter by city (exact match, case-insensitive).
    #[arg(long)]
    pub city: Option<String>,

    /// Filter by ZIP code (repeatable).
    #[arg(long = "zip")]
    pub zips: Vec<String>,

    /// Filter by industry (substring, case-insensitive).
    #[arg(long)]
    pub industry: Option<String>,

    /// Only print/export results with score >= N.
    #[arg(long)]
    pub min_score: Option<i32>,

    /// Export matching top scans to CSV.
    #[arg(long)]
    pub export: Option<PathBuf>,

    /// Read DB and print target counts/samples; zero network calls.
    #[arg(long, default_value_t = false)]
    pub dry_run: bool,

    /// Verbose logging.
    #[arg(long, default_value_t = false)]
    pub verbose: bool,
}
