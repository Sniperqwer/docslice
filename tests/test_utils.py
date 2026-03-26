from __future__ import annotations

from docslice.utils import (
    DEFAULT_USER_AGENT,
    create_http_client,
    normalize_url,
    polite_sleep,
    slugify_title,
)


def test_normalize_url_resolves_relative_path() -> None:
    result = normalize_url("/docs/intro", "https://example.com")
    assert result == "https://example.com/docs/intro"


def test_normalize_url_filters_cross_domain_urls() -> None:
    result = normalize_url("https://other.example.com/docs", "https://example.com")
    assert result is None


def test_normalize_url_filters_anchor_only_urls() -> None:
    result = normalize_url("#section", "https://example.com/docs")
    assert result is None


def test_normalize_url_removes_fragment_and_utm_params() -> None:
    result = normalize_url(
        "/docs/intro/?utm_source=test&keep=1#section",
        "https://example.com",
    )
    assert result == "https://example.com/docs/intro?keep=1"


def test_normalize_url_keeps_root_path_slash() -> None:
    result = normalize_url("/", "https://example.com")
    assert result == "https://example.com/"


def test_slugify_title_handles_empty_values() -> None:
    assert slugify_title("") == "untitled"
    assert slugify_title(None) == "untitled"


def test_slugify_title_truncates_and_uses_underscores() -> None:
    title = "A very long title with spaces that should be truncated after fifty chars"
    assert slugify_title(title) == "a_very_long_title_with_spaces_that_should_be_trunc"


def test_create_http_client_uses_expected_defaults() -> None:
    client = create_http_client()
    try:
        assert client.follow_redirects is True
        assert client.headers["User-Agent"] == DEFAULT_USER_AGENT
        assert client.timeout.connect == 10.0
        assert client.timeout.read == 30.0
    finally:
        client.close()


def test_polite_sleep_returns_delay_with_floor() -> None:
    calls: list[float] = []

    def fake_sleep(value: float) -> None:
        calls.append(value)

    result = polite_sleep(
        0.0,
        sleep_fn=fake_sleep,
        uniform_fn=lambda _start, _end: 0.0,
    )

    assert result == 0.1
    assert calls == [0.1]
