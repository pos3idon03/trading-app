"""SEC EDGAR tool: fetches recent 10-K/10-Q filings for a given ticker.

Uses the SEC EDGAR full-text search API (no API key required).
"""
from typing import Optional

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from utils.logging import get_logger

logger = get_logger(__name__)

EDGAR_COMPANY_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={start}&enddt={end}&forms={forms}"
EDGAR_CIK_LOOKUP_URL = "https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker}&type={form}&dateb=&owner=include&count=5&search_text=&action=getcompany&output=atom"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
EDGAR_FILINGS_BASE = "https://www.sec.gov/Archives/edgar/full-index/"

REQUEST_HEADERS = {
    "User-Agent": "TradingApp research@tradingapp.dev",
    "Accept-Encoding": "gzip, deflate",
}


class SecEdgarInput(BaseModel):
    ticker: str = Field(description="Stock ticker symbol, e.g. AAPL")
    form_type: str = Field(default="10-K", description="SEC form type: 10-K or 10-Q")
    max_filings: int = Field(default=3, ge=1, le=10)


class SecEdgarTool(BaseTool):
    name: str = "sec_edgar_filings"
    description: str = (
        "Fetches recent SEC filings (10-K annual or 10-Q quarterly) for a ticker from EDGAR. "
        "Returns filing dates, accession numbers, and document URLs for fundamental analysis."
    )
    args_schema: type[BaseModel] = SecEdgarInput

    def _run(self, ticker: str, form_type: str = "10-K", max_filings: int = 3) -> str:
        try:
            cik = _resolve_cik(ticker)
            if cik is None:
                return f"Could not find CIK for ticker {ticker}. Ensure it is a valid US-listed company."
            filings = _fetch_recent_filings(cik, form_type, max_filings)
            return _format_filings(ticker, form_type, filings)
        except Exception as exc:
            logger.warning("sec_edgar_tool_error", ticker=ticker, error=str(exc))
            return f"Failed to fetch SEC filings for {ticker}: {exc}"


def _resolve_cik(ticker: str) -> Optional[int]:
    """Look up company CIK number from EDGAR company search by ticker."""
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=&CIK={ticker}&type=10-K&dateb=&owner=include&count=5&search_text=&output=atom"
    with httpx.Client(headers=REQUEST_HEADERS, timeout=15) as client:
        resp = client.get(url)
        resp.raise_for_status()
    import re
    match = re.search(r"/cgi-bin/browse-edgar\?action=getcompany&CIK=(\d+)", resp.text)
    if match:
        return int(match.group(1))
    cik_match = re.search(r"CIK=0*(\d+)", resp.text)
    return int(cik_match.group(1)) if cik_match else None


def _fetch_recent_filings(cik: int, form_type: str, max_filings: int) -> list[dict]:
    """Retrieve recent filing metadata from the EDGAR submissions endpoint."""
    url = EDGAR_SUBMISSIONS_URL.format(cik=cik)
    with httpx.Client(headers=REQUEST_HEADERS, timeout=15) as client:
        resp = client.get(url)
        resp.raise_for_status()
    data = resp.json()

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    filings = []
    for i, form in enumerate(forms):
        if form == form_type and len(filings) < max_filings:
            acc = accessions[i].replace("-", "")
            filings.append({
                "form": form,
                "date": dates[i],
                "accession": accessions[i],
                "document_url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{primary_docs[i]}",
            })
    return filings


def _format_filings(ticker: str, form_type: str, filings: list[dict]) -> str:
    if not filings:
        return f"No {form_type} filings found for {ticker} on EDGAR."
    lines = [f"SEC EDGAR {form_type} filings for {ticker}:\n"]
    for f in filings:
        lines.append(f"  - Filed: {f['date']} | Accession: {f['accession']}")
        lines.append(f"    Document: {f['document_url']}")
    return "\n".join(lines)
