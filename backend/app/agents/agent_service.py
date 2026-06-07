import json
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
from sqlalchemy.orm import Session
from app.core.config import settings
from app.agents.executor import run_agent_loop
from app.models.user import User
from app.services.agent_service import (
    save_agent_conversation,
    get_agent_history,
    get_agent_memory,
    update_agent_memory,
    extract_primary_ticker,
    build_memory_summary,
)
from app.services.backtesting_service import generate_ai_strategy
from app.services.portfolio_service import get_portfolio_overview
from app.services.prediction_service import run_prediction
from app.services.sentiment_service import analyze_sentiment
from app.agents.schema import AgentResponse
from app.rag.services import build_rag_context


def _build_portfolio_context(portfolio_summary: Dict[str, Any]) -> str:
    if not portfolio_summary["portfolios"]:
        return "The user currently has no portfolio holdings on record."

    lines = [
        f"User portfolio count: {portfolio_summary['portfolio_count']}",
        f"Total portfolio value: ${portfolio_summary['total_value']:.2f}",
        f"Total portfolio profit/loss: ${portfolio_summary['total_profit_loss']:.2f}",
        f"Average portfolio risk score: {portfolio_summary['portfolio_risk_score']:.1f}",
        "Holdings:",
    ]
    for holding in portfolio_summary["holdings"]:
        lines.append(
            f" - {holding['ticker']}: {holding['shares']} shares, current ${holding['current_price']:.2f}, "
            f"PnL ${holding['profit_loss']:.2f}, allocation {holding['allocation_percentage']:.1f}%"
        )
    return "\n".join(lines)


def _build_memory_context(memories: List[Dict[str, Any]]) -> str:
    if not memories:
        return "No persistent memory is available for this user yet."

    summaries = [f"{memory['topic']}: {memory['summary']}" for memory in memories]
    return "User memory summary:\n" + "\n".join(summaries)


def _extract_query_ticker(query: str, portfolio_symbols: List[str]) -> Optional[str]:
    symbol = extract_primary_ticker(query, portfolio_symbols)
    if symbol:
        return symbol.upper()
    return None


def _is_strategy_generation_query(query: str) -> bool:
    content = (query or "").lower()
    return "strategy" in content and any(
        kw in content for kw in ["create", "generate", "build", "design", "momentum", "mean reversion", "trend"]
    )


def _compute_recommendation_and_confidence(
    prediction_data: Optional[Dict[str, Any]],
    sentiment_data: Optional[Dict[str, Any]],
    portfolio_summary: Dict[str, Any],
    ticker: Optional[str],
) -> Dict[str, Any]:
    recommendation = "HOLD"
    confidence = 50
    reasoning = []

    if prediction_data and sentiment_data:
        predicted_trend = str(prediction_data.get("trend", "neutral")).upper()
        sentiment_label = str(sentiment_data.get("sentiment", sentiment_data.get("market_sentiment", "neutral"))).upper()

        if predicted_trend == "BULLISH" and sentiment_label == "BULLISH":
            recommendation = "BUY"
            confidence = 75
        elif predicted_trend == "BEARISH" and sentiment_label == "BEARISH":
            recommendation = "SELL"
            confidence = 75
        elif predicted_trend == "BULLISH":
            recommendation = "BUY"
            confidence = 60
        elif predicted_trend == "BEARISH":
            recommendation = "SELL"
            confidence = 60
        else:
            recommendation = "HOLD"
            confidence = 55

        if portfolio_summary["portfolio_risk_score"] > 65:
            confidence -= 10
            reasoning.append("The user's portfolio risk profile is elevated, which tempers the recommendation.")

        if ticker and any(holding["ticker"] == ticker for holding in portfolio_summary["holdings"]):
            reasoning.append(f"The user currently holds {ticker} in their portfolio.")

        if predicted_trend:
            reasoning.append(f"Prediction engine indicates a {predicted_trend.lower()} bias.")
        if sentiment_label:
            reasoning.append(f"Sentiment signals are {sentiment_label.lower()}.")

        r2 = None
        if isinstance(prediction_data.get("evaluation_metrics"), dict):
            r2 = prediction_data["evaluation_metrics"].get("r2")
        if isinstance(r2, (int, float)):
            confidence += min(15, int(r2 * 20))
            reasoning.append(f"Model evaluation score R2={r2:.2f} supports the forecast.")
    else:
        reasoning.append("Insufficient model or sentiment signal to make a high-confidence recommendation.")

    confidence = max(20, min(95, confidence))
    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "reasoning": reasoning,
    }


async def stream_enterprise_analysis(db: Session, user: User, query: str):
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured.")

    portfolio_summary = get_portfolio_overview(db, user.id)
    user_history = get_agent_history(db, user.id)
    memory_context = get_agent_memory(db, user.id)
    query_ticker = _extract_query_ticker(query, portfolio_summary["symbols"])

    save_agent_conversation(db, user.id, "user", query)

    if _is_strategy_generation_query(query):
        strategy_data = await generate_ai_strategy(db, user, query)

        async def _stream_strategy():
            summary_text = (
                f"Generated strategy \"{strategy_data['name']}\" and stored it for the user.\n"
                f"Risk profile: {strategy_data.get('risk_profile', 'N/A')}\n"
                f"Reasoning: {strategy_data.get('reasoning', 'N/A')}\n"
                f"Rules:\n{json.dumps(strategy_data['rules_json'], indent=2)}\n"
            )
            yield summary_text

        return _stream_strategy()

    system_context = _build_portfolio_context(portfolio_summary)
    memory_text = _build_memory_context(memory_context)

    messages = [
        {"role": "system", "content": system_context},
        {"role": "system", "content": memory_text},
    ]

    for history_item in user_history:
        messages.append({"role": history_item["role"], "content": history_item["content"]})

    messages.append({"role": "user", "content": query})

    rag_context = None
    if query_ticker:
        rag_context = await build_rag_context(db, query_ticker, query)
        if rag_context:
            messages.append({"role": "system", "content": rag_context})

    messages.append({"role": "system", "content": "Use available tools to gather any missing market, technical, prediction, or sentiment signals before answering."})

    messages = await run_agent_loop(messages)

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    final_prompt = [
        {"role": "system", "content": "Provide a concise enterprise analyst summary with a recommendation, confidence score, and explainability. Use the portfolio context above and the tool outputs."},
    ]
    final_prompt.extend(messages)
    final_prompt.append({
        "role": "system",
        "content": (
            "Do not fabricate market data. If the query is about a ticker, mention it explicitly. "
            "At the end, provide a short paragraph of rationale that references price, indicators, prediction, sentiment, and portfolio fit."
        ),
    })

    async def _stream():
        partial_text = ""
        async with client.chat.completions.stream(
            model=settings.OPENAI_MODEL,
            messages=final_prompt,
            temperature=0.25,
            max_tokens=650,
        ) as stream:
            async for event in stream:
                if event.type == "response.delta":
                    delta = event.delta
                    if delta is None:
                        continue
                    text = delta.get("content")
                    if text:
                        partial_text += text
                        yield json.dumps({"type": "partial", "text": text}) + "\n"
                elif event.type == "response.error":
                    yield json.dumps({"type": "error", "message": str(event.error)}) + "\n"

        prediction_data = None
        sentiment_data = None
        if query_ticker:
            try:
                prediction_data = run_prediction(query_ticker, "xgboost")
            except Exception:
                prediction_data = None
            try:
                sentiment_data = analyze_sentiment(db, query_ticker)
            except Exception:
                sentiment_data = None

        recommendation_data = _compute_recommendation_and_confidence(
            prediction_data, sentiment_data, portfolio_summary, query_ticker
        )

        save_agent_conversation(db, user.id, "assistant", partial_text)
        if partial_text.strip():
            update_agent_memory(db, user.id, query_ticker or "market theme", build_memory_summary(query, partial_text))

        yield json.dumps(
            {
                "type": "final",
                "payload": {
                    "symbol": query_ticker or "MARKET",
                    "recommendation": recommendation_data["recommendation"],
                    "confidence": recommendation_data["confidence"],
                    "reasoning": recommendation_data["reasoning"],
                    "data": {
                        "query": query,
                        "portfolio_summary": portfolio_summary,
                        "prediction": prediction_data,
                        "sentiment": sentiment_data,
                        "rag_context_used": bool(rag_context),
                    },
                },
            }
        ) + "\n"

    return _stream()
