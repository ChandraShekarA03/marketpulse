import json
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.services.cache_service import cache_response
from app.rag.chunking import chunk_text
from app.rag.embeddings import create_embeddings
from app.models.document import Document, DocumentChunk
from app.core.config import settings

logger = logging.getLogger(__name__)

SEC_HEADERS = {
    "User-Agent": settings.SEC_EDGAR_USER_AGENT,
    "Accept": "application/json, text/html, application/xhtml+xml",
}


def _secure_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


@cache_response(ttl_seconds=86400)
def fetch_cik_for_ticker(ticker: str) -> Optional[str]:
    ticker = ticker.upper().strip()
    url = "https://www.sec.gov/files/company_tickers.json"
    session = _secure_session()
    response = session.get(url, headers=SEC_HEADERS, timeout=20)
    response.raise_for_status()
    data = response.json()

    for company in data.values():
        if company.get("ticker") == ticker:
            cik = str(company.get("cik", "")).zfill(10)
            return cik
    return None


@cache_response(ttl_seconds=3600)
def fetch_company_submissions(cik: str) -> Dict[str, List[Dict[str, str]]]:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    session = _secure_session()
    response = session.get(url, headers=SEC_HEADERS, timeout=20)
    response.raise_for_status()
    data = response.json()

    filings = []
    recent = data.get("filings", {}).get("recent", {})
    types = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_documents = recent.get("primaryDocument", [])

    for idx, form_type in enumerate(types):
        filings.append(
            {
                "filing_type": form_type,
                "accession_number": accession_numbers[idx],
                "filing_date": filing_dates[idx],
                "primary_document": primary_documents[idx],
            }
        )
    return {"filings": filings, "company_name": data.get("name", "")}


def _clean_source_text(raw: str) -> str:
    content = re.sub(r"<script.*?>.*?<\/script>", "", raw, flags=re.S | re.I)
    content = re.sub(r"<style.*?>.*?<\/style>", "", raw, flags=re.S | re.I)
    content = re.sub(r"<[^>]+>", " ", content)
    content = re.sub(r"\s+", " ", content)
    return content.strip()


def _build_filing_url(cik: str, accession: str, document_name: str) -> str:
    accession_id = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_id}/{document_name}"


async def ingest_filings(db, ticker: str, top_types: Optional[List[str]] = None) -> Dict[str, int]:
    ticker = ticker.upper().strip()
    top_types = top_types or ["10-K", "10-Q", "8-K"]

    cik = fetch_cik_for_ticker(ticker)
    if not cik:
        raise ValueError(f"Unable to find SEC CIK for ticker {ticker}.")

    submissions = fetch_company_submissions(cik)
    filings = submissions.get("filings", [])
    company_name = submissions.get("company_name", ticker)

    chosen = []
    seen = set()
    for filing in filings:
        if filing["filing_type"] in top_types and filing["filing_type"] not in seen:
            chosen.append(filing)
            seen.add(filing["filing_type"])
        if len(chosen) >= len(top_types):
            break

    created = 0
    chunks_created = 0
    for filing in chosen:
        source_url = _build_filing_url(cik, filing["accession_number"], filing["primary_document"])
        existing = db.query(Document).filter(Document.source_url == source_url).first()
        if existing:
            logger.info(f"Skipping already ingested filing: {source_url}")
            continue

        session = _secure_session()
        response = session.get(source_url, headers=SEC_HEADERS, timeout=30)
        response.raise_for_status()
        raw_text = _clean_source_text(response.text)
        if not raw_text:
            logger.warning(f"No text extracted from filing {source_url}")
            continue

        document = Document(
            company=company_name,
            ticker=ticker,
            filing_type=filing["filing_type"],
            filing_date=datetime.fromisoformat(filing["filing_date"]),
            source_url=source_url,
            document_metadata=json.dumps({
                "accession_number": filing["accession_number"],
                "primary_document": filing["primary_document"],
            }),
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        created += 1

        chunks = chunk_text(raw_text)
        embeddings = await create_embeddings(chunks)

        for index, (chunk_text_value, embedding_vector) in enumerate(zip(chunks, embeddings)):
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_text=chunk_text_value,
                chunk_index=index,
                embedding=embedding_vector,
            )
            db.add(chunk)
            chunks_created += 1

        db.commit()

    return {"documents_ingested": created, "chunks_ingested": chunks_created}
