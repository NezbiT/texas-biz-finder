use thiserror::Error;
use url::Url;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum UrlNormError {
    #[error("empty url")]
    Empty,
    #[error("unsupported scheme: {0}")]
    UnsupportedScheme(String),
    #[error("invalid url: {0}")]
    Invalid(String),
}

/// Normalize a lead website URL for homepage fetch.
///
/// - Trim
/// - Prepend `https://` when scheme is missing
/// - Reject non-http(s)
/// - Strip fragments and common tracking params
/// - Keep path + remaining query (never invent paths)
pub fn normalize_url(raw: &str) -> Result<String, UrlNormError> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err(UrlNormError::Empty);
    }

    let with_scheme = if trimmed.contains("://") {
        trimmed.to_string()
    } else {
        format!("https://{trimmed}")
    };

    let mut url = Url::parse(&with_scheme).map_err(|e| UrlNormError::Invalid(e.to_string()))?;

    match url.scheme() {
        "http" | "https" => {}
        other => return Err(UrlNormError::UnsupportedScheme(other.to_string())),
    }

    url.set_fragment(None);

    // Collect keys to drop (utm_*, fbclid, gclid), then rebuild query.
    let pairs: Vec<(String, String)> = url
        .query_pairs()
        .filter(|(k, _)| {
            let key = k.as_ref();
            !(key.eq_ignore_ascii_case("fbclid")
                || key.eq_ignore_ascii_case("gclid")
                || key.to_ascii_lowercase().starts_with("utm_"))
        })
        .map(|(k, v)| (k.into_owned(), v.into_owned()))
        .collect();

    if pairs.is_empty() {
        url.set_query(None);
    } else {
        url.query_pairs_mut().clear().extend_pairs(pairs);
    }

    Ok(url.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn prepends_https() {
        assert_eq!(
            normalize_url("example.com/path").unwrap(),
            "https://example.com/path"
        );
    }

    #[test]
    fn strips_fragment_and_tracking() {
        let out = normalize_url(
            "https://example.com/page?utm_source=x&id=1&fbclid=abc&gclid=y#frag",
        )
        .unwrap();
        assert_eq!(out, "https://example.com/page?id=1");
    }

    #[test]
    fn rejects_non_http() {
        assert!(matches!(
            normalize_url("ftp://example.com"),
            Err(UrlNormError::UnsupportedScheme(_))
        ));
    }

    #[test]
    fn empty_errors() {
        assert_eq!(normalize_url("  "), Err(UrlNormError::Empty));
    }
}
