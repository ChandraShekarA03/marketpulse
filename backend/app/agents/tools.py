from typing import Dict, Any, Callable
import json
from app.services.stock_service import get_stock_data
from app.services.indicator_service import generate_indicators
from app.services.prediction_service import run_prediction
from app.services.sentiment_service import analyze_sentiment

# Tool schema definitions for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Fetch real-time stock data and price for a given ticker symbol.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g., AAPL"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_technical_indicators",
            "description": "Generate technical indicators (RSI, MACD, etc.) and trend signals for a given stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g., AAPL"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_prediction",
            "description": "Run the machine learning prediction engine for a given stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g., AAPL"
                    },
                    "model_type": {
                        "type": "string",
                        "enum": ["linear", "randomforest", "xgboost", "lstm"],
                        "description": "The ML model to use. Default is xgboost."
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sentiment",
            "description": "Analyze recent news sentiment for a given stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g., AAPL"
                    }
                },
                "required": ["symbol"]
            }
        }
    }
]

# Registry mapping tool names to actual service functions
def execute_tool(name: str, arguments: Dict[str, Any]) -> Any:
    symbol = arguments.get("symbol")
    
    if name == "get_stock_price":
        return get_stock_data(symbol)
    elif name == "get_technical_indicators":
        # Convert Pydantic schemas to dict if necessary, but usually FastAPI handles this
        # To be safe in python logic, let's dump model if it has model_dump
        res = generate_indicators(symbol)
        if hasattr(res.get("indicators"), "model_dump"):
            res["indicators"] = res["indicators"].model_dump()
        elif hasattr(res.get("indicators"), "dict"):
            res["indicators"] = res["indicators"].dict()
        return res
    elif name == "get_prediction":
        model_type = arguments.get("model_type", "xgboost")
        return run_prediction(symbol, model_type)
    elif name == "get_sentiment":
        return analyze_sentiment(symbol)
    else:
        raise ValueError(f"Unknown tool: {name}")
