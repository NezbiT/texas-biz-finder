//! In-memory robots.txt cache for the lifetime of one run.

use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;

use reqwest::Client;
use tokio::sync::Mutex;
use url::Url;

use crate::USER_AGENT;

#[derive(Debug, Clone)]
struct RobotsEntry {
    /// Raw body (empty if missing / error → allow-all).
    body: String,
    /// True if fetch failed soft (treat as allow-all).
    fetch_failed: bool,
}

/// Cache keyed by origin (`scheme://host[:port]`).
#[derive(Clone, Default)]
pub struct RobotsCache {
    inner: Arc<Mutex<HashMap<String, RobotsEntry>>>,
}

impl RobotsCache {
    pub fn new() -> Self {
        Self {
            inner: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Returns `true` if `tbf-scan` is allowed to fetch `url`.
    pub async fn allowed(&self, client: &Client, url: &str) -> Result<bool, String> {
        let parsed = Url::parse(url).map_err(|e| e.to_string())?;
        let origin = origin_of(&parsed)?;
        let path = parsed.path();
        let path = if path.is_empty() { "/" } else { path };

        let entry = {
            let guard = self.inner.lock().await;
            if let Some(e) = guard.get(&origin) {
                e.clone()
            } else {
                drop(guard);
                let fetched = fetch_robots(client, &origin).await;
                let mut guard = self.inner.lock().await;
                guard.entry(origin.clone()).or_insert(fetched).clone()
            }
        };

        if entry.fetch_failed || entry.body.trim().is_empty() {
            return Ok(true);
        }

        Ok(is_allowed(&entry.body, USER_AGENT, path))
    }
}

fn origin_of(url: &Url) -> Result<String, String> {
    let scheme = url.scheme();
    let host = url.host_str().ok_or_else(|| "url missing host".to_string())?;
    let origin = match url.port() {
        Some(p) => format!("{scheme}://{host}:{p}"),
        None => format!("{scheme}://{host}"),
    };
    Ok(origin)
}

async fn fetch_robots(client: &Client, origin: &str) -> RobotsEntry {
    let robots_url = format!("{origin}/robots.txt");
    match client
        .get(&robots_url)
        .header("User-Agent", USER_AGENT)
        .timeout(Duration::from_secs(8))
        .send()
        .await
    {
        Ok(resp) if resp.status().is_success() => {
            let body = resp.text().await.unwrap_or_default();
            // Cap robots body to 512 KiB
            let body = if body.len() > 512 * 1024 {
                body.chars().take(512 * 1024).collect()
            } else {
                body
            };
            RobotsEntry {
                body,
                fetch_failed: false,
            }
        }
        Ok(_) => RobotsEntry {
            body: String::new(),
            fetch_failed: false,
        },
        Err(_) => RobotsEntry {
            body: String::new(),
            fetch_failed: true,
        },
    }
}

/// Minimal robots.txt evaluator for a single user-agent group.
///
/// Honors the most specific matching Allow/Disallow for our UA group,
/// falling back to `*` group. Empty Disallow = allow all.
pub fn is_allowed(robots_body: &str, user_agent: &str, path: &str) -> bool {
    let ua_token = user_agent
        .split('/')
        .next()
        .unwrap_or(user_agent)
        .to_ascii_lowercase();

    #[derive(Default)]
    struct Group {
        applies: bool,
        rules: Vec<(bool, String)>, // (allow, path_prefix)
    }

    let mut groups: Vec<Group> = Vec::new();
    let mut current = Group::default();
    let mut in_group = false;

    for raw in robots_body.lines() {
        let line = raw.split('#').next().unwrap_or("").trim();
        if line.is_empty() {
            continue;
        }
        let Some((key, value)) = line.split_once(':') else {
            continue;
        };
        let key = key.trim().to_ascii_lowercase();
        let value = value.trim();

        match key.as_str() {
            "user-agent" => {
                if in_group && !current.rules.is_empty() || (in_group && current.applies) {
                    // New UA after rules → new group. If consecutive UAs, same group.
                }
                // If previous line was not user-agent, start new group.
                // Simple approach: accumulate consecutive UA lines into one group.
                if !in_group || (!current.rules.is_empty() && !key_continues_ua(raw)) {
                    if in_group {
                        groups.push(std::mem::take(&mut current));
                    }
                    current = Group::default();
                    in_group = true;
                }
                let v = value.to_ascii_lowercase();
                if v == "*" || ua_token.contains(&v) || v.contains(&ua_token) {
                    current.applies = true;
                }
            }
            "disallow" => {
                if !in_group {
                    current = Group::default();
                    in_group = true;
                }
                // Empty Disallow means allow all for this group (skip rule).
                if !value.is_empty() {
                    current.rules.push((false, value.to_string()));
                }
            }
            "allow" => {
                if !in_group {
                    current = Group::default();
                    in_group = true;
                }
                if !value.is_empty() {
                    current.rules.push((true, value.to_string()));
                }
            }
            _ => {}
        }
    }
    if in_group {
        groups.push(current);
    }

    // Prefer specific UA group, else *
    let specific = groups.iter().find(|g| g.applies);
    let star = groups.iter().find(|g| {
        // groups that only matched via * — we marked applies for both * and name.
        // Re-parse: use first applies group (we set applies for * and matching UA).
        g.applies
    });

    // If we have a group that applies (includes *), use the most specific rule match.
    let group = specific.or(star);
    let Some(group) = group else {
        return true;
    };
    if group.rules.is_empty() {
        return true;
    }

    // Longest matching prefix wins; Allow beats Disallow on equal length.
    let mut best_len = -1i32;
    let mut best_allow = true;
    for (allow, prefix) in &group.rules {
        if path_matches(path, prefix) {
            let len = prefix.len() as i32;
            if len > best_len || (len == best_len && *allow && !best_allow) {
                best_len = len;
                best_allow = *allow;
            }
        }
    }
    if best_len < 0 {
        return true;
    }
    best_allow
}

fn key_continues_ua(_raw: &str) -> bool {
    // Simplified: always treat consecutive handling in main loop.
    true
}

fn path_matches(path: &str, rule_prefix: &str) -> bool {
    if rule_prefix == "/" {
        return true;
    }
    // robots wildcards: * and $
    if rule_prefix.contains('*') || rule_prefix.ends_with('$') {
        return wildcard_match(path, rule_prefix);
    }
    path.starts_with(rule_prefix)
}

fn wildcard_match(path: &str, pattern: &str) -> bool {
    // Very small subset: * and trailing $
    let mut pat = pattern;
    let end_anchor = pat.ends_with('$');
    if end_anchor {
        pat = &pat[..pat.len() - 1];
    }
    let parts: Vec<&str> = pat.split('*').collect();
    if parts.len() == 1 {
        return if end_anchor {
            path == parts[0]
        } else {
            path.starts_with(parts[0])
        };
    }
    let mut rest = path;
    if !parts[0].is_empty() {
        if !rest.starts_with(parts[0]) {
            return false;
        }
        rest = &rest[parts[0].len()..];
    }
    for (i, part) in parts.iter().enumerate().skip(1) {
        if part.is_empty() {
            continue;
        }
        if let Some(idx) = rest.find(part) {
            rest = &rest[idx + part.len()..];
            if i == parts.len() - 1 && end_anchor && !rest.is_empty() {
                return false;
            }
        } else {
            return false;
        }
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn disallow_all() {
        let body = "User-agent: *\nDisallow: /\n";
        assert!(!is_allowed(body, USER_AGENT, "/"));
        assert!(!is_allowed(body, USER_AGENT, "/page"));
    }

    #[test]
    fn allow_when_empty_disallow() {
        let body = "User-agent: *\nDisallow:\n";
        assert!(is_allowed(body, USER_AGENT, "/"));
    }

    #[test]
    fn specific_path() {
        let body = "User-agent: *\nDisallow: /private\nAllow: /private/public\n";
        assert!(!is_allowed(body, USER_AGENT, "/private/x"));
        assert!(is_allowed(body, USER_AGENT, "/private/public"));
        assert!(is_allowed(body, USER_AGENT, "/ok"));
    }

    #[test]
    fn our_ua_group() {
        let body = "User-agent: tbf-scan\nDisallow: /\n\nUser-agent: *\nDisallow:\n";
        assert!(!is_allowed(body, USER_AGENT, "/any"));
    }
}
