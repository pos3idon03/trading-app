"""Tests for AI agent tools: SEC EDGAR, FRED, and News Sentiment.

All external HTTP calls are mocked to keep tests fast and offline.
"""
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# SecEdgarTool
# ---------------------------------------------------------------------------


class TestSecEdgarTool:
    def test_returns_filing_summary_on_success(self):
        from features.ai_agents.tools.sec_edgar_tool import SecEdgarTool, _format_filings

        filings = [
            {"form": "10-K", "date": "2024-02-01", "accession": "0001234567-24-000001", "document_url": "https://www.sec.gov/filing.htm"},
        ]
        result = _format_filings("AAPL", "10-K", filings)
        assert "AAPL" in result
        assert "2024-02-01" in result
        assert "https://www.sec.gov" in result

    def test_empty_filings_message(self):
        from features.ai_agents.tools.sec_edgar_tool import _format_filings

        result = _format_filings("AAPL", "10-K", [])
        assert "No 10-K filings found" in result

    def test_tool_handles_http_error_gracefully(self):
        from features.ai_agents.tools.sec_edgar_tool import SecEdgarTool

        tool = SecEdgarTool()
        with patch("features.ai_agents.tools.sec_edgar_tool._resolve_cik", side_effect=Exception("network error")):
            result = tool._run(ticker="AAPL")
        assert "Failed to fetch" in result
        assert "AAPL" in result

    def test_tool_returns_message_when_cik_not_found(self):
        from features.ai_agents.tools.sec_edgar_tool import SecEdgarTool

        tool = SecEdgarTool()
        with patch("features.ai_agents.tools.sec_edgar_tool._resolve_cik", return_value=None):
            result = tool._run(ticker="ZZZZ")
        assert "Could not find CIK" in result

    def test_fetch_recent_filings_filters_by_form_type(self):
        from features.ai_agents.tools.sec_edgar_tool import _fetch_recent_filings

        mock_data = {
            "filings": {
                "recent": {
                    "form": ["10-K", "10-Q", "10-K", "8-K"],
                    "filingDate": ["2024-02-01", "2023-11-01", "2023-02-01", "2024-01-15"],
                    "accessionNumber": ["0001-24-001", "0001-23-002", "0001-23-001", "0001-24-002"],
                    "primaryDocument": ["doc1.htm", "doc2.htm", "doc3.htm", "doc4.htm"],
                }
            }
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            filings = _fetch_recent_filings(cik=320193, form_type="10-K", max_filings=5)

        assert all(f["form"] == "10-K" for f in filings)
        assert len(filings) == 2


# ---------------------------------------------------------------------------
# FredTool
# ---------------------------------------------------------------------------


class TestFredTool:
    def test_returns_no_key_message_when_key_missing(self):
        from features.ai_agents.tools.fred_tool import FredTool

        tool = FredTool()
        with patch("features.ai_agents.tools.fred_tool.get_settings") as mock_settings:
            mock_settings.return_value.fred_api_key = ""
            result = tool._run(series_ids=["DFF"])
        assert "FRED_API_KEY" in result

    def test_format_series_with_data(self):
        from features.ai_agents.tools.fred_tool import _format_series

        data = {
            "observations": [
                {"date": "2024-05-01", "value": "5.33"},
                {"date": "2024-04-01", "value": "5.33"},
            ]
        }
        result = _format_series("DFF", data)
        assert "DFF" in result
        assert "5.33" in result
        assert "2024-05-01" in result

    def test_format_series_handles_missing_values(self):
        from features.ai_agents.tools.fred_tool import _format_series

        data = {"observations": [{"date": "2024-05-01", "value": "."}]}
        result = _format_series("DGS10", data)
        assert "N/A" in result

    def test_format_series_handles_none_data(self):
        from features.ai_agents.tools.fred_tool import _format_series

        result = _format_series("CPIAUCSL", None)
        assert "fetch failed" in result

    def test_fetch_series_handles_http_error(self):
        from features.ai_agents.tools.fred_tool import _fetch_series

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception("timeout")
            result = _fetch_series("DFF", "test_key", 5)
        assert result is None

    def test_tool_runs_with_multiple_series(self):
        from features.ai_agents.tools.fred_tool import FredTool

        tool = FredTool()
        mock_data = {"observations": [{"date": "2024-05-01", "value": "5.33"}]}
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data

        with (
            patch("features.ai_agents.tools.fred_tool.get_settings") as mock_settings,
            patch("httpx.Client") as mock_client,
        ):
            mock_settings.return_value.fred_api_key = "test_key"
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            result = tool._run(series_ids=["DFF", "DGS10"], observation_count=1)

        assert "DFF" in result
        assert "DGS10" in result


# ---------------------------------------------------------------------------
# NewsSentimentTool
# ---------------------------------------------------------------------------


class TestNewsSentimentTool:
    def test_returns_no_key_message_when_key_missing(self):
        from features.ai_agents.tools.news_sentiment_tool import NewsSentimentTool

        tool = NewsSentimentTool()
        with patch("features.ai_agents.tools.news_sentiment_tool.get_settings") as mock_settings:
            mock_settings.return_value.newsapi_key = ""
            result = tool._run(ticker="AAPL")
        assert "NEWSAPI_KEY" in result

    def test_format_articles_output(self):
        from features.ai_agents.tools.news_sentiment_tool import _format_articles

        articles = [
            {
                "title": "Apple Reports Record Revenue",
                "source": {"name": "Reuters"},
                "publishedAt": "2024-05-01T10:00:00Z",
                "description": "Apple Inc. reported record-breaking quarterly revenue.",
            }
        ]
        result = _format_articles("AAPL", articles)
        assert "AAPL" in result
        assert "Apple Reports Record Revenue" in result
        assert "Reuters" in result

    def test_returns_no_news_when_empty(self):
        from features.ai_agents.tools.news_sentiment_tool import NewsSentimentTool

        tool = NewsSentimentTool()
        with (
            patch("features.ai_agents.tools.news_sentiment_tool.get_settings") as mock_settings,
            patch("features.ai_agents.tools.news_sentiment_tool._fetch_articles", return_value=[]),
        ):
            mock_settings.return_value.newsapi_key = "test_key"
            result = tool._run(ticker="AAPL")
        assert "No recent news" in result

    def test_fetch_articles_handles_http_error(self):
        from features.ai_agents.tools.news_sentiment_tool import _fetch_articles

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception("timeout")
            articles = _fetch_articles("AAPL", "test_key", 7)
        assert articles == []

    def test_fetch_articles_returns_list_on_success(self):
        from features.ai_agents.tools.news_sentiment_tool import _fetch_articles

        mock_data = {
            "articles": [
                {"title": "Test headline", "source": {"name": "Reuters"}, "publishedAt": "2024-05-01T00:00:00Z", "description": "Test."}
            ]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            articles = _fetch_articles("AAPL", "test_key", 7)
        assert len(articles) == 1
        assert articles[0]["title"] == "Test headline"
