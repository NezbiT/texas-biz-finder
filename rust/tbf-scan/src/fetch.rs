//! HTTP fetch with politeness, timeouts, body limit, and one retry.

use std::sync::Arc;
use std::time::{Duration, Instant};

use governor::{
    clock::DefaultClock,
    state::{InMemoryState, NotKeyed},
    RateLimiter,
};
use rand::Rng;
use reqwest::{Client, redirect::Policy};
use tokio::sync::Semaphore;
use url::Url;

use crate::robots::RobotsCache;
use crate::score::{score_html, score_unreachable, HtmlScoreInput, NetMeta, ScoreResult};
use crate::{
    BODY_LIMIT_BYTES, CONNECT_TIMEOUT_SECS, MAX_REDIRECTS, TOTAL_TIMEOUT_SECS, USER_AGENT,
};

// re-export path: nonzero is via governor — use std NonZeroU32 instead
use std::num::NonZeroU32;

/// Result of scanning one lead URL.
#[derive(Debug, Clone)]
pub struct FetchOutcome {
    pub lead_id: i64,
    pub url_attempted: String,
    pub final_url: Option<String>,
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

/// Shared fetch stack: client, robots cache, global semaphore, per-host 1 rps.
pub struct FetchStack {
    pub client: Client,
    pub robots: RobotsCache,
    pub global: Arc<Semaphore>,
    /// Per-host rate limiters (1 request / second).
    host_limiters: dashmap_shim::HostLimiters,
}

// Lightweight host limiter map without adding dashmap if avoidable —
// use tokio Mutex + HashMap instead.
mod dashmap_shim {
    use std::collections::HashMap;
    use std::num::NonZeroU32;
    use std::sync::Arc;

    use governor::{
        clock::DefaultClock,
        state::{InMemoryState, NotKeyed},
        Quota, RateLimiter,
    };
    use tokio::sync::Mutex;

    pub type Limiter = RateLimiter<NotKeyed, InMemoryState, DefaultClock>;

    #[derive(Clone, Default)]
    pub struct HostLimiters {
        inner: Arc<Mutex<HashMap<String, Arc<Limiter>>>>,
    }

    impl HostLimiters {
        pub async fn limiter_for(&self, host: &str) -> Arc<Limiter> {
            let mut guard = self.inner.lock().await;
            guard
                .entry(host.to_string())
                .or_insert_with(|| {
                    let q = Quota::per_second(NonZeroU32::new(1).expect("1 rps"));
                    Arc::new(RateLimiter::direct(q))
                })
                .clone()
        }
    }
}

impl FetchStack {
    pub fn new(concurrency: usize) -> anyhow::Result<Self> {
        let client = Client::builder()
            .user_agent(USER_AGENT)
            .connect_timeout(Duration::from_secs(CONNECT_TIMEOUT_SECS))
            .timeout(Duration::from_secs(TOTAL_TIMEOUT_SECS))
            .redirect(Policy::limited(MAX_REDIRECTS))
            .pool_max_idle_per_host(1)
            .build()?;

        Ok(Self {
            client,
            robots: RobotsCache::new(),
            global: Arc::new(Semaphore::new(concurrency.max(1))),
            host_limiters: dashmap_shim::HostLimiters::default(),
        })
    }

    pub async fn scan_lead(
        &self,
        lead_id: i64,
        url_attempted: &str,
        zip: Option<&str>,
    ) -> FetchOutcome {
        let _permit = match self.global.acquire().await {
            Ok(p) => p,
            Err(_) => {
                return failure_outcome(lead_id, url_attempted, "parse", zip);
            }
        };

        // robots first
        match self.robots.allowed(&self.client, url_attempted).await {
            Ok(false) => {
                let scored = score_unreachable("robots", &NetMeta::default(), zip);
                return FetchOutcome {
                    lead_id,
                    url_attempted: url_attempted.to_string(),
                    final_url: None,
                    reachable: false,
                    http_status: None,
                    ttfb_ms: None,
                    total_ms: None,
                    bytes: None,
                    is_https: None,
                    tls_ok: None,
                    error_kind: "robots".into(),
                    score: scored.score,
                    signals_json: scored.signals_json,
                };
            }
            Ok(true) => {}
            Err(e) => {
                tracing::debug!(lead_id, error = %e, "robots check error; treating as allow");
            }
        }

        let host = Url::parse(url_attempted)
            .ok()
            .and_then(|u| u.host_str().map(|h| h.to_string()))
            .unwrap_or_else(|| "unknown".into());

        let limiter = self.host_limiters.limiter_for(&host).await;
        limiter.until_ready().await;

        // First attempt + optional single retry on timeout/5xx
        match self.attempt(url_attempted).await {
            Attempt::Done(outcome) => finalize(lead_id, url_attempted, outcome, zip),
            Attempt::Retryable(_partial) => {
                let backoff_ms = 1500u64 + rand::thread_rng().gen_range(0..500);
                tokio::time::sleep(Duration::from_millis(backoff_ms)).await;
                limiter.until_ready().await;
                match self.attempt(url_attempted).await {
                    Attempt::Done(outcome) | Attempt::Retryable(outcome) => {
                        finalize(lead_id, url_attempted, outcome, zip)
                    }
                    // unreachable
                }
            }
        }
    }

    async fn attempt(&self, url: &str) -> Attempt {
        let start = Instant::now();
        let is_https = url.starts_with("https://");

        let response = match self.client.get(url).send().await {
            Ok(r) => r,
            Err(e) => {
                let kind = classify_reqwest_error(&e);
                let total_ms = start.elapsed().as_millis() as i64;
                return if kind == "timeout" {
                    Attempt::Retryable(RawOutcome {
                        final_url: None,
                        reachable: false,
                        http_status: None,
                        ttfb_ms: None,
                        total_ms: Some(total_ms),
                        bytes: None,
                        is_https: Some(is_https),
                        tls_ok: if kind == "tls" {
                            Some(false)
                        } else if is_https {
                            None
                        } else {
                            Some(true)
                        },
                        error_kind: kind.into(),
                        body: None,
                    })
                } else {
                    Attempt::Done(RawOutcome {
                        final_url: None,
                        reachable: false,
                        http_status: None,
                        ttfb_ms: None,
                        total_ms: Some(total_ms),
                        bytes: None,
                        is_https: Some(is_https),
                        tls_ok: if kind == "tls" {
                            Some(false)
                        } else if is_https {
                            None
                        } else {
                            Some(true)
                        },
                        error_kind: kind.into(),
                        body: None,
                    })
                };
            }
        };

        let ttfb_ms = start.elapsed().as_millis() as i64;
        let status = response.status();
        let final_url = response.url().to_string();
        let final_https = final_url.starts_with("https://");

        // 5xx → retryable once
        if status.is_server_error() {
            let total_ms = start.elapsed().as_millis() as i64;
            return Attempt::Retryable(RawOutcome {
                final_url: Some(final_url),
                reachable: true,
                http_status: Some(status.as_u16() as i32),
                ttfb_ms: Some(ttfb_ms),
                total_ms: Some(total_ms),
                bytes: None,
                is_https: Some(final_https),
                tls_ok: Some(final_https),
                error_kind: "http".into(),
                body: None,
            });
        }

        // Read body with hard limit
        match read_body_limited(response, BODY_LIMIT_BYTES).await {
            Ok((bytes_len, body)) => {
                let total_ms = start.elapsed().as_millis() as i64;
                let error_kind = if status.is_client_error() {
                    "http".into()
                } else {
                    "none".into()
                };
                Attempt::Done(RawOutcome {
                    final_url: Some(final_url),
                    reachable: true,
                    http_status: Some(status.as_u16() as i32),
                    ttfb_ms: Some(ttfb_ms),
                    total_ms: Some(total_ms),
                    bytes: Some(bytes_len as i64),
                    is_https: Some(final_https),
                    tls_ok: Some(final_https),
                    error_kind,
                    body: if status.is_success() {
                        Some(body)
                    } else {
                        // still parse error pages for signals when small
                        Some(body)
                    },
                })
            }
            Err(BodyErr::TooLarge { bytes }) => {
                let total_ms = start.elapsed().as_millis() as i64;
                Attempt::Done(RawOutcome {
                    final_url: Some(final_url),
                    reachable: true,
                    http_status: Some(status.as_u16() as i32),
                    ttfb_ms: Some(ttfb_ms),
                    total_ms: Some(total_ms),
                    bytes: Some(bytes as i64),
                    is_https: Some(final_https),
                    tls_ok: Some(final_https),
                    error_kind: "too_large".into(),
                    body: None,
                })
            }
            Err(BodyErr::Io(kind)) => {
                let total_ms = start.elapsed().as_millis() as i64;
                let retryable = kind == "timeout";
                let outcome = RawOutcome {
                    final_url: Some(final_url),
                    reachable: false,
                    http_status: Some(status.as_u16() as i32),
                    ttfb_ms: Some(ttfb_ms),
                    total_ms: Some(total_ms),
                    bytes: None,
                    is_https: Some(final_https),
                    tls_ok: Some(final_https),
                    error_kind: kind.into(),
                    body: None,
                };
                if retryable {
                    Attempt::Retryable(outcome)
                } else {
                    Attempt::Done(outcome)
                }
            }
        }
    }
}

enum Attempt {
    Done(RawOutcome),
    Retryable(RawOutcome),
}

#[derive(Debug, Clone)]
struct RawOutcome {
    final_url: Option<String>,
    reachable: bool,
    http_status: Option<i32>,
    ttfb_ms: Option<i64>,
    total_ms: Option<i64>,
    bytes: Option<i64>,
    is_https: Option<bool>,
    tls_ok: Option<bool>,
    error_kind: String,
    body: Option<String>,
}

enum BodyErr {
    TooLarge { bytes: usize },
    Io(&'static str),
}

async fn read_body_limited(
    response: reqwest::Response,
    limit: usize,
) -> Result<(usize, String), BodyErr> {
    use futures::StreamExt;
    let mut stream = response.bytes_stream();
    let mut buf: Vec<u8> = Vec::new();
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.map_err(|_| BodyErr::Io("timeout"))?;
        if buf.len() + chunk.len() > limit {
            return Err(BodyErr::TooLarge {
                bytes: buf.len() + chunk.len(),
            });
        }
        buf.extend_from_slice(&chunk);
    }
    let len = buf.len();
    let body = String::from_utf8_lossy(&buf).into_owned();
    Ok((len, body))
}

fn classify_reqwest_error(e: &reqwest::Error) -> &'static str {
    if e.is_timeout() {
        return "timeout";
    }
    if e.is_redirect() {
        return "redirect_loop";
    }
    if e.is_connect() {
        let msg = e.to_string().to_ascii_lowercase();
        if msg.contains("dns") || msg.contains("resolve") || msg.contains("name or service") {
            return "dns";
        }
        if msg.contains("tls") || msg.contains("certificate") || msg.contains("ssl") {
            return "tls";
        }
        if msg.contains("refused") || msg.contains("reset") {
            return "refused";
        }
        return "refused";
    }
    let msg = e.to_string().to_ascii_lowercase();
    if msg.contains("dns") || msg.contains("resolve") {
        return "dns";
    }
    if msg.contains("tls") || msg.contains("certificate") || msg.contains("ssl") {
        return "tls";
    }
    if msg.contains("redirect") {
        return "redirect_loop";
    }
    "timeout"
}

fn net_from_raw(raw: &RawOutcome) -> NetMeta {
    NetMeta {
        http_status: raw.http_status,
        is_https: raw.is_https,
        tls_ok: raw.tls_ok,
        ttfb_ms: raw.ttfb_ms,
        total_ms: raw.total_ms,
        bytes: raw.bytes,
        final_url: raw.final_url.clone(),
    }
}

fn finalize(lead_id: i64, url_attempted: &str, raw: RawOutcome, zip: Option<&str>) -> FetchOutcome {
    let meta = net_from_raw(&raw);
    let scored: ScoreResult = if raw.error_kind == "none" {
        if let (Some(body), Some(status), Some(https), Some(tls), Some(ttfb), Some(total), Some(bytes)) = (
            raw.body.as_deref(),
            raw.http_status,
            raw.is_https,
            raw.tls_ok,
            raw.ttfb_ms,
            raw.total_ms,
            raw.bytes,
        ) {
            let final_url = raw.final_url.as_deref().unwrap_or(url_attempted);
            score_html(&HtmlScoreInput {
                html: body,
                http_status: status,
                is_https: https,
                tls_ok: tls,
                ttfb_ms: ttfb,
                total_ms: total,
                bytes,
                final_url,
                zip,
            })
        } else {
            score_unreachable("parse", &meta, zip)
        }
    } else if raw.error_kind == "http" {
        // May still have body for partial signals, but score via status primarily
        if let Some(body) = raw.body.as_deref() {
            if let (Some(status), Some(https), Some(tls), Some(ttfb), Some(total), Some(bytes)) = (
                raw.http_status,
                raw.is_https,
                raw.tls_ok,
                raw.ttfb_ms,
                raw.total_ms,
                raw.bytes,
            ) {
                let final_url = raw.final_url.as_deref().unwrap_or(url_attempted);
                let mut r = score_html(&HtmlScoreInput {
                    html: body,
                    http_status: status,
                    is_https: https,
                    tls_ok: tls,
                    ttfb_ms: ttfb,
                    total_ms: total,
                    bytes,
                    final_url,
                    zip,
                });
                // ensure error_kind stays http
                r.signals.error_kind = "http".into();
                if let Ok(mut v) = serde_json::from_str::<serde_json::Value>(&r.signals_json) {
                    v["error_kind"] = serde_json::json!("http");
                    r.signals_json = v.to_string();
                }
                r
            } else {
                score_unreachable("http", &meta, zip)
            }
        } else {
            score_unreachable("http", &meta, zip)
        }
    } else {
        score_unreachable(&raw.error_kind, &meta, zip)
    };

    FetchOutcome {
        lead_id,
        url_attempted: url_attempted.to_string(),
        final_url: raw.final_url,
        reachable: raw.reachable && raw.error_kind == "none",
        http_status: raw.http_status,
        ttfb_ms: raw.ttfb_ms,
        total_ms: raw.total_ms,
        bytes: raw.bytes,
        is_https: raw.is_https,
        tls_ok: raw.tls_ok,
        error_kind: if scored.signals.error_kind.is_empty() {
            raw.error_kind
        } else {
            scored.signals.error_kind.clone()
        },
        score: scored.score,
        signals_json: scored.signals_json,
    }
}

fn failure_outcome(lead_id: i64, url: &str, kind: &str, zip: Option<&str>) -> FetchOutcome {
    let scored = score_unreachable(kind, &NetMeta::default(), zip);
    FetchOutcome {
        lead_id,
        url_attempted: url.to_string(),
        final_url: None,
        reachable: false,
        http_status: None,
        ttfb_ms: None,
        total_ms: None,
        bytes: None,
        is_https: None,
        tls_ok: None,
        error_kind: kind.into(),
        score: scored.score,
        signals_json: scored.signals_json,
    }
}

// silence unused import warning path for Quota types used in submodule
#[allow(dead_code)]
type _Gov = RateLimiter<NotKeyed, InMemoryState, DefaultClock>;
#[allow(dead_code)]
fn _nz() -> NonZeroU32 {
    NonZeroU32::new(1).unwrap()
}
