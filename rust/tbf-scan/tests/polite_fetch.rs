//! Local wiremock server: robots + per-host rate limiting (no real network).

use std::sync::Arc;
use std::time::{Duration, Instant};

use tbf_scan::fetch::FetchStack;
use tbf_scan::robots::is_allowed;
use tbf_scan::USER_AGENT;
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

#[tokio::test]
async fn robots_disallow_never_fetches_page() {
    let server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/robots.txt"))
        .respond_with(ResponseTemplate::new(200).set_body_string("User-agent: *\nDisallow: /\n"))
        .mount(&server)
        .await;

    // Page must never be requested when robots disallows.
    Mock::given(method("GET"))
        .and(path("/"))
        .respond_with(ResponseTemplate::new(200).set_body_string("<html><title>Nope</title></html>"))
        .expect(0)
        .mount(&server)
        .await;

    let stack = FetchStack::new(4).unwrap();
    let url = format!("{}/", server.uri());
    let outcome = stack.scan_lead(99, &url, None).await;

    assert_eq!(outcome.error_kind, "robots");
    assert_eq!(outcome.score, None);
}

#[tokio::test]
async fn per_host_limit_is_about_one_rps() {
    let server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/robots.txt"))
        .respond_with(ResponseTemplate::new(404))
        .mount(&server)
        .await;

    Mock::given(method("GET"))
        .and(path("/page"))
        .respond_with(
            ResponseTemplate::new(200).set_body_string(
                r#"<!doctype html><html><head>
                <meta name="viewport" content="w">
                <title>Page</title></head><body>ok</body></html>"#,
            ),
        )
        .mount(&server)
        .await;

    let stack = Arc::new(FetchStack::new(8).unwrap());
    let url = format!("{}/page", server.uri());
    let start = Instant::now();

    let mut handles = Vec::new();
    for i in 0..3 {
        let stack = Arc::clone(&stack);
        let url = url.clone();
        handles.push(tokio::spawn(async move {
            stack.scan_lead(i, &url, None).await
        }));
    }
    for h in handles {
        let o = h.await.unwrap();
        assert_eq!(o.error_kind, "none", "{o:?}");
    }

    let elapsed = start.elapsed();
    // 3 requests at 1 rps → at least ~2 seconds of spacing
    assert!(
        elapsed >= Duration::from_millis(1800),
        "expected ~1 rps pacing, elapsed={elapsed:?}"
    );
}

#[test]
fn robots_parser_unit() {
    assert!(!is_allowed(
        "User-agent: *\nDisallow: /secret\n",
        USER_AGENT,
        "/secret/x"
    ));
    assert!(is_allowed(
        "User-agent: *\nDisallow: /secret\n",
        USER_AGENT,
        "/public"
    ));
}
