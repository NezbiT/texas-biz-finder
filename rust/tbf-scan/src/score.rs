//! Scoring model: independent signals summed and capped at 100.

use chrono::{Datelike, Utc};
use regex::Regex;
use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::sync::OnceLock;

use crate::hispanic_zips::zip_hispanic_flags;

/// Every signal is recorded in `signals_json` regardless of final score.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ScanSignals {
    pub unreachable: bool,
    pub error_kind: String,
    pub http_status: Option<i32>,
    pub is_https: Option<bool>,
    pub tls_ok: Option<bool>,
    pub ttfb_ms: Option<i64>,
    pub total_ms: Option<i64>,
    pub bytes: Option<i64>,
    pub final_url: Option<String>,
    pub missing_viewport: bool,
    pub missing_title: bool,
    pub title_bare_or_home: bool,
    pub title: Option<String>,
    pub missing_meta_description: bool,
    pub has_jsonld_org: bool,
    pub has_tel_link: bool,
    pub copyright_year: Option<i32>,
    pub copyright_stale: bool,
    pub body_over_2_5_mib: bool,
    pub site_builder: Option<String>,
    pub has_spanish: bool,
    pub high_hispanic_zip: bool,
    pub zip_unknown: bool,
    pub points: Vec<PointAward>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PointAward {
    pub signal: String,
    pub points: i32,
}

#[derive(Debug, Clone)]
pub struct ScoreResult {
    /// 0–100, or None if robots / unparseable.
    pub score: Option<i32>,
    pub signals: ScanSignals,
    pub signals_json: String,
}

fn re_copyright() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"(?i)(?:©|&copy;|copyright)\s*(?:19|20)\d{2}").expect("copyright re")
    })
}

fn re_year() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"(19|20)\d{2}").expect("year re"))
}

fn re_spanish_text() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"(?i)español|espanol|\bes\b").expect("es text re"))
}

fn re_es_path() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"(?i)/es(?:/|$|\?|#)").expect("es path re"))
}

/// Site-builder fingerprints (HTML / headers body).
fn detect_builder(html: &str) -> Option<&'static str> {
    let lower = html.to_ascii_lowercase();
    if lower.contains("wix.com") || lower.contains("wixstatic") || lower.contains("_wix_browser") {
        return Some("wix");
    }
    if lower.contains("squarespace") || lower.contains("static.squarespace") {
        return Some("squarespace");
    }
    if lower.contains("weebly") || lower.contains("editmysite.com") {
        return Some("weebly");
    }
    if lower.contains("godaddy") || lower.contains("secureserver.net") || lower.contains("gd-header")
    {
        return Some("godaddy");
    }
    if lower.contains("duda.co")
        || lower.contains("dudaone")
        || (lower.contains("dm-") && lower.contains("duda"))
    {
        return Some("duda");
    }
    None
}

fn extract_title(doc: &Html) -> Option<String> {
    let sel = Selector::parse("title").ok()?;
    doc.select(&sel)
        .next()
        .map(|n| n.text().collect::<String>().trim().to_string())
        .filter(|s| !s.is_empty())
}

fn has_viewport(doc: &Html) -> bool {
    let Ok(sel) = Selector::parse(r#"meta[name="viewport"]"#) else {
        return false;
    };
    doc.select(&sel).any(|el| {
        el.value()
            .attr("content")
            .map(|c| !c.trim().is_empty())
            .unwrap_or(false)
    })
}

fn has_meta_description(doc: &Html) -> bool {
    let Ok(sel) = Selector::parse(r#"meta[name="description"]"#) else {
        return false;
    };
    doc.select(&sel).any(|el| {
        el.value()
            .attr("content")
            .map(|c| !c.trim().is_empty())
            .unwrap_or(false)
    })
}

fn has_jsonld_org(html: &str, doc: &Html) -> bool {
    let Ok(sel) = Selector::parse(r#"script[type="application/ld+json"]"#) else {
        return false;
    };
    for el in doc.select(&sel) {
        let text = el.text().collect::<String>();
        let lower = text.to_ascii_lowercase();
        if lower.contains("localbusiness") || lower.contains("\"organization\"") {
            return true;
        }
    }
    // Fallback raw substring for minified / odd markup
    let lower = html.to_ascii_lowercase();
    lower.contains("\"@type\":\"localbusiness\"")
        || lower.contains("\"@type\": \"localbusiness\"")
        || lower.contains("\"@type\":\"organization\"")
        || lower.contains("\"@type\": \"organization\"")
}

fn has_tel_link(doc: &Html) -> bool {
    let Ok(sel) = Selector::parse(r#"a[href^="tel:"]"#) else {
        return false;
    };
    doc.select(&sel).next().is_some()
}

fn copyright_year(html: &str) -> Option<i32> {
    let m = re_copyright().find(html)?;
    let y = re_year().find(m.as_str())?;
    y.as_str().parse().ok()
}

fn has_spanish(doc: &Html, html: &str) -> bool {
    // html[lang^="es"]
    if let Ok(sel) = Selector::parse("html[lang]") {
        if doc.select(&sel).any(|el| {
            el.value()
                .attr("lang")
                .map(|l| l.to_ascii_lowercase().starts_with("es"))
                .unwrap_or(false)
        }) {
            return true;
        }
    }
    // link[hreflang^="es"]
    if let Ok(sel) = Selector::parse("link[hreflang]") {
        if doc.select(&sel).any(|el| {
            el.value()
                .attr("hreflang")
                .map(|l| l.to_ascii_lowercase().starts_with("es"))
                .unwrap_or(false)
        }) {
            return true;
        }
    }
    // a[href*="/es"]
    if let Ok(sel) = Selector::parse("a[href]") {
        for el in doc.select(&sel) {
            if let Some(href) = el.value().attr("href") {
                if re_es_path().is_match(href) {
                    return true;
                }
            }
            let text = el.text().collect::<String>();
            if re_spanish_text().is_match(&text) {
                return true;
            }
        }
    }
    // body text match
    re_spanish_text().is_match(html)
}

fn title_is_bare_or_home(title: &str, final_url: Option<&str>) -> bool {
    let t = title.trim();
    if t.eq_ignore_ascii_case("home") || t.eq_ignore_ascii_case("homepage") {
        return true;
    }
    if let Some(url) = final_url {
        if let Ok(parsed) = url::Url::parse(url) {
            if let Some(host) = parsed.host_str() {
                let host_bare = host.trim_start_matches("www.");
                if t.eq_ignore_ascii_case(host) || t.eq_ignore_ascii_case(host_bare) {
                    return true;
                }
            }
        }
    }
    false
}

/// Network-level fields shared by unreachable + HTML scoring.
#[derive(Debug, Clone, Default)]
pub struct NetMeta {
    pub http_status: Option<i32>,
    pub is_https: Option<bool>,
    pub tls_ok: Option<bool>,
    pub ttfb_ms: Option<i64>,
    pub total_ms: Option<i64>,
    pub bytes: Option<i64>,
    pub final_url: Option<String>,
}

/// Inputs for full HTML scoring after a successful fetch.
#[derive(Debug, Clone)]
pub struct HtmlScoreInput<'a> {
    pub html: &'a str,
    pub http_status: i32,
    pub is_https: bool,
    pub tls_ok: bool,
    pub ttfb_ms: i64,
    pub total_ms: i64,
    pub bytes: i64,
    pub final_url: &'a str,
    pub zip: Option<&'a str>,
}

/// Score from network-level failure (no HTML body to parse).
pub fn score_unreachable(error_kind: &str, meta: &NetMeta, zip: Option<&str>) -> ScoreResult {
    let (high_hispanic, zip_unknown) = zip_hispanic_flags(zip);
    let mut signals = ScanSignals {
        unreachable: true,
        error_kind: error_kind.to_string(),
        http_status: meta.http_status,
        is_https: meta.is_https,
        tls_ok: meta.tls_ok,
        ttfb_ms: meta.ttfb_ms,
        total_ms: meta.total_ms,
        bytes: meta.bytes,
        final_url: meta.final_url.clone(),
        high_hispanic_zip: high_hispanic,
        zip_unknown,
        ..Default::default()
    };

    // robots / unparseable → score NULL
    if error_kind == "robots" || error_kind == "parse" {
        let signals_json = serde_json::to_string(&signals).unwrap_or_else(|_| "{}".into());
        return ScoreResult {
            score: None,
            signals,
            signals_json,
        };
    }

    let mut points: Vec<PointAward> = Vec::new();

    match error_kind {
        "dns" | "timeout" | "refused" => {
            points.push(PointAward {
                signal: "unreachable".into(),
                points: 40,
            });
        }
        "tls" => {
            points.push(PointAward {
                signal: "no_https_or_tls_failure".into(),
                points: 20,
            });
            // TLS failure often pairs with reach attempt; still weak digital presence
        }
        "http" => {
            if let Some(status) = meta.http_status {
                if (500..600).contains(&status) {
                    points.push(PointAward {
                        signal: "http_5xx".into(),
                        points: 35,
                    });
                } else if (400..500).contains(&status) {
                    points.push(PointAward {
                        signal: "http_4xx".into(),
                        points: 28,
                    });
                }
            }
        }
        "too_large" => {
            points.push(PointAward {
                signal: "body_over_2_5_mib".into(),
                points: 5,
            });
        }
        "redirect_loop" => {
            points.push(PointAward {
                signal: "unreachable".into(),
                points: 40,
            });
        }
        _ => {}
    }

    if (meta.is_https == Some(false) || meta.tls_ok == Some(false))
        && !points.iter().any(|p| p.signal == "no_https_or_tls_failure")
    {
        points.push(PointAward {
            signal: "no_https_or_tls_failure".into(),
            points: 20,
        });
    }

    let sum: i32 = points.iter().map(|p| p.points).sum();
    let score = Some(sum.min(100));
    signals.points = points;
    let signals_json = serde_json::to_string(&signals).unwrap_or_else(|_| "{}".into());
    ScoreResult {
        score,
        signals,
        signals_json,
    }
}

/// Full HTML scoring after a successful fetch.
pub fn score_html(input: &HtmlScoreInput<'_>) -> ScoreResult {
    let (high_hispanic, zip_unknown) = zip_hispanic_flags(input.zip);
    let mut signals = ScanSignals {
        unreachable: false,
        error_kind: "none".into(),
        http_status: Some(input.http_status),
        is_https: Some(input.is_https),
        tls_ok: Some(input.tls_ok),
        ttfb_ms: Some(input.ttfb_ms),
        total_ms: Some(input.total_ms),
        bytes: Some(input.bytes),
        final_url: Some(input.final_url.to_string()),
        high_hispanic_zip: high_hispanic,
        zip_unknown,
        ..Default::default()
    };

    let mut points: Vec<PointAward> = Vec::new();

    // HTTP status on final URL
    if (500..600).contains(&input.http_status) {
        points.push(PointAward {
            signal: "http_5xx".into(),
            points: 35,
        });
    } else if (400..500).contains(&input.http_status) {
        points.push(PointAward {
            signal: "http_4xx".into(),
            points: 28,
        });
    }

    if !input.is_https || !input.tls_ok {
        points.push(PointAward {
            signal: "no_https_or_tls_failure".into(),
            points: 20,
        });
    }

    if input.ttfb_ms > 2500 {
        points.push(PointAward {
            signal: "ttfb_gt_2500".into(),
            points: 12,
        });
    } else if input.ttfb_ms >= 1200 {
        points.push(PointAward {
            signal: "ttfb_1200_2500".into(),
            points: 6,
        });
    }

    const MIB_2_5: i64 = (2.5 * 1024.0 * 1024.0) as i64;
    if input.bytes > MIB_2_5 {
        signals.body_over_2_5_mib = true;
        points.push(PointAward {
            signal: "body_over_2_5_mib".into(),
            points: 5,
        });
    }

    let doc = Html::parse_document(input.html);

    let title = extract_title(&doc);
    signals.title = title.clone();
    match &title {
        None => {
            signals.missing_title = true;
            points.push(PointAward {
                signal: "missing_title".into(),
                points: 10,
            });
        }
        Some(t) if title_is_bare_or_home(t, Some(input.final_url)) => {
            signals.title_bare_or_home = true;
            points.push(PointAward {
                signal: "title_bare_or_home".into(),
                points: 6,
            });
        }
        _ => {}
    }

    if !has_viewport(&doc) {
        signals.missing_viewport = true;
        points.push(PointAward {
            signal: "missing_viewport".into(),
            points: 16,
        });
    }

    if !has_meta_description(&doc) {
        signals.missing_meta_description = true;
        points.push(PointAward {
            signal: "missing_meta_description".into(),
            points: 7,
        });
    }

    let has_org = has_jsonld_org(input.html, &doc);
    signals.has_jsonld_org = has_org;
    if !has_org {
        points.push(PointAward {
            signal: "no_jsonld_org".into(),
            points: 7,
        });
    }

    let tel = has_tel_link(&doc);
    signals.has_tel_link = tel;
    if !tel {
        points.push(PointAward {
            signal: "no_tel_link".into(),
            points: 8,
        });
    }

    let year = copyright_year(input.html);
    signals.copyright_year = year;
    let current_year = Utc::now().year();
    if let Some(y) = year {
        if y <= current_year - 3 {
            signals.copyright_stale = true;
            points.push(PointAward {
                signal: "copyright_stale".into(),
                points: 9,
            });
        }
    }

    if let Some(builder) = detect_builder(input.html) {
        signals.site_builder = Some(builder.to_string());
        points.push(PointAward {
            signal: "site_builder".into(),
            points: 8,
        });
    }

    let spanish = has_spanish(&doc, input.html);
    signals.has_spanish = spanish;
    if high_hispanic && !spanish {
        points.push(PointAward {
            signal: "no_spanish_high_hispanic_zip".into(),
            points: 10,
        });
    }

    let sum: i32 = points.iter().map(|p| p.points).sum();
    let score = Some(sum.min(100));
    signals.points = points;

    // Also embed a compact debug object for operators
    let signals_json = serde_json::to_string(&signals).unwrap_or_else(|_| {
        json!({ "error": "serialize_failed" }).to_string()
    });

    ScoreResult {
        score,
        signals,
        signals_json,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn clean_modern_site_low_score() {
        let html = r#"<!doctype html>
        <html lang="en">
        <head>
          <meta name="viewport" content="width=device-width">
          <meta name="description" content="Best bakery in town">
          <title>Hill Country Bakery — Fredericksburg</title>
          <script type="application/ld+json">
            {"@type":"LocalBusiness","name":"Hill Country Bakery"}
          </script>
        </head>
        <body>
          <a href="tel:+15125551212">Call us</a>
          <p>Copyright 2026 Hill Country Bakery</p>
        </body>
        </html>"#;
        let r = score_html(&HtmlScoreInput {
            html,
            http_status: 200,
            is_https: true,
            tls_ok: true,
            ttfb_ms: 200,
            total_ms: 400,
            bytes: 12_000,
            final_url: "https://hillcountrybakery.example/",
            zip: Some("78624"),
        });
        assert!(r.score.unwrap() < 20, "score={}", r.score.unwrap());
        assert!(!r.signals.missing_viewport);
        assert!(r.signals.has_jsonld_org);
        assert!(r.signals.has_tel_link);
    }

    #[test]
    fn ancient_bare_site_high_score() {
        let html = r#"<!doctype html>
        <html>
        <head><title>Home</title></head>
        <body><p>Welcome. &copy; 2015 Old Shop</p></body>
        </html>"#;
        let r = score_html(&HtmlScoreInput {
            html,
            http_status: 200,
            is_https: false,
            tls_ok: false,
            ttfb_ms: 3000,
            total_ms: 4000,
            bytes: 800,
            final_url: "http://oldshop.example/",
            zip: Some("78624"),
        });
        // no https 20 + viewport 16 + ttfb 12 + title home 6 + meta 7 + jsonld 7 + tel 8 + copyright 9
        assert!(r.score.unwrap() >= 70, "score={}", r.score.unwrap());
    }

    #[test]
    fn builder_fingerprint() {
        let html = r#"<!doctype html>
        <html><head>
          <meta name="viewport" content="width=device-width">
          <title>My Wix Site</title>
        </head>
        <body>
          <script src="https://static.wixstatic.com/foo.js"></script>
        </body></html>"#;
        let r = score_html(&HtmlScoreInput {
            html,
            http_status: 200,
            is_https: true,
            tls_ok: true,
            ttfb_ms: 100,
            total_ms: 200,
            bytes: 5000,
            final_url: "https://user.wixsite.com/x",
            zip: None,
        });
        assert_eq!(r.signals.site_builder.as_deref(), Some("wix"));
        assert!(r.signals.points.iter().any(|p| p.signal == "site_builder"));
    }

    #[test]
    fn bilingual_avoids_spanish_penalty() {
        let html = r#"<!doctype html>
        <html lang="es">
        <head>
          <meta name="viewport" content="width=device-width">
          <meta name="description" content="Panadería">
          <title>Panadería del Valle</title>
          <script type="application/ld+json">{"@type":"Organization"}</script>
        </head>
        <body>
          <a href="tel:+19155551212">Llámanos</a>
          <a href="/es/menu">Español</a>
          <p>Copyright 2026</p>
        </body></html>"#;
        let r = score_html(&HtmlScoreInput {
            html,
            http_status: 200,
            is_https: true,
            tls_ok: true,
            ttfb_ms: 100,
            total_ms: 200,
            bytes: 4000,
            final_url: "https://panaderia.example/",
            zip: Some("79901"), // El Paso — high Hispanic
        });
        assert!(r.signals.has_spanish);
        assert!(r.signals.high_hispanic_zip);
        assert!(!r
            .signals
            .points
            .iter()
            .any(|p| p.signal == "no_spanish_high_hispanic_zip"));
    }

    #[test]
    fn empty_html_many_points() {
        let r = score_html(&HtmlScoreInput {
            html: "",
            http_status: 200,
            is_https: true,
            tls_ok: true,
            ttfb_ms: 100,
            total_ms: 100,
            bytes: 0,
            final_url: "https://empty.example/",
            zip: None,
        });
        assert!(r.score.unwrap() >= 40);
        assert!(r.signals.missing_title);
    }

    #[test]
    fn http_error_pages() {
        let r = score_unreachable(
            "http",
            &NetMeta {
                http_status: Some(404),
                is_https: Some(true),
                tls_ok: Some(true),
                ttfb_ms: Some(50),
                total_ms: Some(80),
                final_url: Some("https://x.example/missing".into()),
                ..Default::default()
            },
            None,
        );
        assert_eq!(r.score, Some(28));

        let r5 = score_unreachable(
            "http",
            &NetMeta {
                http_status: Some(503),
                is_https: Some(true),
                tls_ok: Some(true),
                ..Default::default()
            },
            None,
        );
        assert_eq!(r5.score, Some(35));
    }

    #[test]
    fn robots_null_score() {
        let r = score_unreachable("robots", &NetMeta::default(), None);
        assert_eq!(r.score, None);
        assert_eq!(r.signals.error_kind, "robots");
    }

    #[test]
    fn dns_unreachable_40() {
        let r = score_unreachable("dns", &NetMeta::default(), None);
        assert_eq!(r.score, Some(40));
    }
}
