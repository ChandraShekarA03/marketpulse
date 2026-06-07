import json
import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI
from app.core.config import settings
from app.agents.prompts import SYSTEM_PROMPT
from app.agents.tools import TOOLS, execute_tool

logger = logging.getLogger(__name__)

async def run_agent_loop(messages: List[Dict[str, Any]], max_iterations: int = 5):
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured.")

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def _normalize_message(message_obj: Any) -> Dict[str, Any]:
        if isinstance(message_obj, dict):
            return message_obj
        if hasattr(message_obj, "model_dump"):
            return message_obj.model_dump()

        normalized = {
            "role": getattr(message_obj, "role", None),
            "content": getattr(message_obj, "content", None),
        }
        tool_calls = getattr(message_obj, "tool_calls", None)
        if tool_calls:
            normalized["tool_calls"] = [
                {
                    "id": getattr(tool_call, "id", None),
                    "function": {
                        "name": getattr(tool_call.function, "name", None),
                        "arguments": getattr(tool_call.function, "arguments", None),
                    },
                }
                for tool_call in tool_calls
            ]
        return normalized

    # Rate limiting basic check
    import time
    if not hasattr(run_agent_loop, "last_call"):
        run_agent_loop.last_call = 0
    if time.time() - run_agent_loop.last_call < 1.0:
        await asyncio.sleep(1.0 - (time.time() - run_agent_loop.last_call))
    run_agent_loop.last_call = time.time()

    for _ in range(max_iterations):
        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
        except Exception as e:
            logger.warning(f"Model {settings.OPENAI_MODEL} failed: {e}. Falling back to gpt-3.5-turbo.")
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            
        tokens = response.usage.total_tokens
        # Approx cost for gpt-4o-mini is $0.15 / 1M input + $0.60 / 1M output tokens, we'll estimate 0.30 avg
        cost = (tokens / 1_000_000) * 0.30
        logger.info(f"AI Cost Tracking | Model: {response.model} | Tokens: {tokens} | Est Cost: ${cost:.6f}")

        message = response.choices[0].message
        normalized_message = _normalize_message(message)
        messages.append(normalized_message)

        if not normalized_message.get("tool_calls"):
            break

        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
                logger.info(f"Agent executing tool {function_name} with args {arguments}")
                tool_result = execute_tool(function_name, arguments)
            except Exception as e:
                logger.error(f"Error executing tool {function_name}: {e}")
                tool_result = {"error": str(e)}

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": json.dumps(tool_result, default=str),
                }
            )

    return messages
