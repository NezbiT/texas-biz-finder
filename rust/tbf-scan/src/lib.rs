//! tbf-scan — lightweight, polite first-pass website lead scorer.
//!
//! Read-only against `leads`. Creates only `site_scans` + indexes + `v_top_leads`.

pub mod cli;
pub mod db;
pub mod export;
pub mod fetch;
pub mod hispanic_zips;
pub mod robots;
pub mod score;
pub mod url_norm;
pub mod writer;

pub use cli::Args;
pub use db::{ensure_schema, LeadRow, ScanFilters};
pub use score::{score_html, HtmlScoreInput, NetMeta, ScanSignals, ScoreResult};
pub use url_norm::normalize_url;

pub const USER_AGENT: &str =
    "tbf-scan/0.1 (+https://zerodigitx.com; hello@zerodigitx.com)";

pub const CHANNEL_CAPACITY: usize = 256;
pub const DEFAULT_CONCURRENCY: usize = 64;
pub const CONNECT_TIMEOUT_SECS: u64 = 8;
pub const TOTAL_TIMEOUT_SECS: u64 = 18;
pub const BODY_LIMIT_BYTES: usize = 4 * 1024 * 1024;
pub const MAX_REDIRECTS: usize = 4;
