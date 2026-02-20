"""Tests for browser_fetcher module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.app.services.browser_fetcher import BrowserHTMLFetcher, BrowserFetchOptions


class TestBrowserFetchOptions:
    """Tests for BrowserFetchOptions dataclass."""

    def test_default_options(self):
        """Should create options with default values."""
        options = BrowserFetchOptions()
        assert options.headless is True
        assert options.timeout_ms == 20_000
        assert options.wait_until == "networkidle"
        assert "Mozilla" in options.user_agent
        assert options.slow_mo_ms == 300
        assert options.post_load_wait_ms == 1_500

    def test_custom_options(self):
        """Should allow custom option values."""
        options = BrowserFetchOptions(
            headless=False,
            timeout_ms=30_000,
            wait_until="load",
            user_agent="Custom Agent",
            slow_mo_ms=500,
            post_load_wait_ms=2_000,
        )
        assert options.headless is False
        assert options.timeout_ms == 30_000
        assert options.wait_until == "load"
        assert options.user_agent == "Custom Agent"
        assert options.slow_mo_ms == 500
        assert options.post_load_wait_ms == 2_000


class TestBrowserHTMLFetcher:
    """Tests for BrowserHTMLFetcher class."""

    def test_init_with_default_options(self):
        """Should initialize with default options."""
        fetcher = BrowserHTMLFetcher()
        assert fetcher._options.headless is True

    def test_init_with_custom_options(self):
        """Should initialize with custom options."""
        options = BrowserFetchOptions(headless=False)
        fetcher = BrowserHTMLFetcher(options)
        assert fetcher._options.headless is False

    @patch("playwright.sync_api.sync_playwright")
    def test_fetch_successful(self, mock_sync_playwright):
        """Should fetch HTML successfully."""
        # Setup mock
        mock_playwright = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()

        mock_page.content.return_value = "<html><body>Test Content</body></html>"
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        # Execute
        fetcher = BrowserHTMLFetcher()
        result = fetcher.fetch("http://example.com")

        # Assert
        assert result == "<html><body>Test Content</body></html>"
        mock_playwright.chromium.launch.assert_called_once()
        mock_page.goto.assert_called_once_with(
            "http://example.com",
            wait_until="networkidle",
            timeout=20_000,
        )
        mock_page.wait_for_timeout.assert_called_once_with(1_500)

    @patch("playwright.sync_api.sync_playwright")
    def test_fetch_with_rj_block_page_retry(self, mock_sync_playwright):
        """Should retry with visible browser when RJ block page detected."""
        # Setup mock - first call returns block page, second returns normal
        mock_playwright = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()

        # First call returns block page
        mock_page.content.return_value = (
            "<html>Secretaria de Estado de Fazenda do Rio de Janeiro</html>"
        )
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        # Execute
        fetcher = BrowserHTMLFetcher()
        result = fetcher.fetch("http://example.com")

        # Assert - should retry with headless=False
        assert mock_playwright.chromium.launch.call_count == 2
        # First call with headless=True
        assert mock_playwright.chromium.launch.call_args_list[0][1]["headless"] is True
        # Second call with headless=False
        assert mock_playwright.chromium.launch.call_args_list[1][1]["headless"] is False

    @patch("playwright.sync_api.sync_playwright")
    def test_fetch_no_retry_when_not_headless(self, mock_sync_playwright):
        """Should not retry when headless is already False."""
        # Setup mock
        mock_playwright = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()

        mock_page.content.return_value = (
            "<html>Secretaria de Estado de Fazenda do Rio de Janeiro</html>"
        )
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        # Execute with headless=False
        options = BrowserFetchOptions(headless=False)
        fetcher = BrowserHTMLFetcher(options)
        result = fetcher.fetch("http://example.com")

        # Assert - should not retry since already not headless
        assert mock_playwright.chromium.launch.call_count == 1
        assert mock_playwright.chromium.launch.call_args[1]["headless"] is False

    @patch("playwright.sync_api.sync_playwright")
    def test_fetch_uses_custom_user_agent(self, mock_sync_playwright):
        """Should use custom user agent in context."""
        mock_playwright = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()

        mock_page.content.return_value = "<html>Test</html>"
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        custom_ua = "Custom User Agent 1.0"
        options = BrowserFetchOptions(user_agent=custom_ua)
        fetcher = BrowserHTMLFetcher(options)
        fetcher.fetch("http://example.com")

        # Assert user agent was passed to new_context
        mock_browser.new_context.assert_called_once_with(
            user_agent=custom_ua,
            locale="pt-BR",
        )

    @patch("playwright.sync_api.sync_playwright")
    def test_fetch_uses_correct_launch_options(self, mock_sync_playwright):
        """Should use correct launch options."""
        mock_playwright = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()

        mock_page.content.return_value = "<html>Test</html>"
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        options = BrowserFetchOptions(headless=False, slow_mo_ms=500)
        fetcher = BrowserHTMLFetcher(options)
        fetcher.fetch("http://example.com")

        # Assert launch was called with correct options
        mock_playwright.chromium.launch.assert_called_with(
            headless=False,
            slow_mo=500,
        )

    @patch("playwright.sync_api.sync_playwright")
    def test_fetch_closes_browser_and_context(self, mock_sync_playwright):
        """Should close browser and context after fetching."""
        mock_playwright = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()

        mock_page.content.return_value = "<html>Test</html>"
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        fetcher = BrowserHTMLFetcher()
        fetcher.fetch("http://example.com")

        # Assert close was called
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()

    @patch("playwright.sync_api.sync_playwright")
    def test_fetch_uses_correct_timeout(self, mock_sync_playwright):
        """Should use correct timeout from options."""
        mock_playwright = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()

        mock_page.content.return_value = "<html>Test</html>"
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        options = BrowserFetchOptions(timeout_ms=30_000, post_load_wait_ms=2_000)
        fetcher = BrowserHTMLFetcher(options)
        fetcher.fetch("http://example.com")

        # Assert timeout was used
        mock_page.goto.assert_called_once_with(
            "http://example.com",
            wait_until="networkidle",
            timeout=30_000,
        )
        mock_page.wait_for_timeout.assert_called_once_with(2_000)
