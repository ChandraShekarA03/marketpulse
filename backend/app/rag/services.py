from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.rag.retriever import retrieve_relevant_chunks, has_rag_context


def _build_prompt(question: str, chunks: List[Dict[str, Any]]) -> str:
    prompt_lines = [
        "You are an Institutional Research Copilot. Use the provided SEC filing excerpts to answer the user's question accurately.",
        "Cite sources using `[SOURCE n]` format where `n` is the excerpt index.",
        "Do not hallucinate or invent facts. Base your response only on the provided excerpts.",
        "",
        f"Question: {question}",
        "",
        "Excerpts:",
    ]

    for index, chunk in enumerate(chunks):
        prompt_lines.append(
            f"[SOURCE {index}] {chunk['filing_type']} ({chunk['filing_date']}) - {chunk['source_url']}\n{chunk['chunk_text']}\n"
        )

    prompt_lines.append("\nAnswer:")
    return "\n".join(prompt_lines)


def _build_sources(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unique_sources = []
    seen_urls = set()
    for idx, chunk in enumerate(chunks):
        if chunk["source_url"] not in seen_urls:
            unique_sources.append(
                {
                    "source_url": chunk["source_url"],
                    "filing_type": chunk["filing_type"],
                    "filing_date": chunk["filing_date"],
                }
            )
            seen_urls.add(chunk["source_url"])
    return unique_sources


from app.services.cache_service import cache_response

@cache_response(ttl_seconds=3600)
async def query_company_rag(
    db: Session,
    ticker: str,
    question: str,
    top_k: int = 4,
) -> Dict[str, Any]:
    ticker = ticker.upper().strip()
    chunks = await retrieve_relevant_chunks(db, ticker, question, top_k=top_k)
    if not chunks:
        return {
            "answer": f"No SEC filing content has been ingested for {ticker}. Please ingest filings first.",
            "sources": [],
            "citations": [],
        }

    prompt = _build_prompt(question, chunks)
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are an expert institutional research assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=700,
    )

    answer = response.choices[0].message.content.strip()
    sources = _build_sources(chunks)
    citations = [f"[SOURCE {idx}] {chunk['filing_type']} {chunk['filing_date']}" for idx, chunk in enumerate(chunks)]

    return {
        "answer": answer,
        "sources": sources,
        "citations": citations,
    }


def query_uses_rag(question: str, ticker: Optional[str]) -> bool:
    if not ticker:
        return False

    lower = question.lower()
    safe_keywords = [
        "risk",
        "guidance",
        "revenue",
        "earnings",
        "disclosure",
        "SEC",
        "10-k",
        "10-q",
        "8-k",
        "transcript",
        "lawsuit",
        "competit",
        "restructur",
        "margin",
        "cash flow",
        "legal",
        "govt",
    ]
    return any(keyword in lower for keyword in safe_keywords)


async def build_rag_context(db: Session, ticker: str, question: str, top_k: int = 3) -> Optional[str]:
    if not query_uses_rag(question, ticker):
        return None

    chunks = await retrieve_relevant_chunks(db, ticker, question, top_k=top_k)
    if not chunks:
        return None

    context_lines = [
        "Relevant SEC filing excerpts are available for this ticker. Use them to ground your answer:",
    ]
    for index, chunk in enumerate(chunks):
        context_lines.append(
            f"[SOURCE {index}] {chunk['filing_type']} {chunk['filing_date']} {chunk['source_url']}\n{chunk['chunk_text']}"
        )

    return "\n\n".join(context_lines)
