from __future__ import annotations

from firered_poc.config import AppConfig
from firered_poc.server import connection_urls, format_startup_banner


def test_connection_urls_specific_host() -> None:
    assert connection_urls("192.168.1.10", 8000) == ["ws://192.168.1.10:8000/ws"]


def test_connection_urls_wildcard_has_loopback() -> None:
    urls = connection_urls("0.0.0.0", 8000)
    assert "ws://127.0.0.1:8000/ws" in urls
    assert all(url.endswith(":8000/ws") for url in urls)


def test_startup_banner_contains_endpoints() -> None:
    text = format_startup_banner(AppConfig(), "127.0.0.1", 8000)
    assert "FireRedASR2S ASR backend" in text
    assert "ws://127.0.0.1:8000/ws" in text
    assert "http://127.0.0.1:8000/health" in text
