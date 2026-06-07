import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, get_db
from app.models.user import User
from app.schemas.strategy import StrategyCreate, StrategyResponse, StrategyAIResponse, StrategyGenerateRequest
from app.services.backtesting_service import create_strategy, get_user_strategies, generate_ai_strategy

router = APIRouter(prefix="/strategies", tags=["Strategies"])


@router.post("", response_model=StrategyResponse)
def create_user_strategy(
    strategy_in: StrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if "entry" not in strategy_in.rules_json or "exit" not in strategy_in.rules_json:
        raise HTTPException(status_code=400, detail="rules_json must contain both entry and exit arrays.")

    strategy = create_strategy(
        db=db,
        user_id=current_user.id,
        name=strategy_in.name,
        description=strategy_in.description,
        rules_json=strategy_in.rules_json,
    )

    return StrategyResponse(
        id=strategy.id,
        user_id=strategy.user_id,
        name=strategy.name,
        description=strategy.description,
        rules_json=json.loads(strategy.rules_json),
        created_at=strategy.created_at,
    )


@router.get("", response_model=List[StrategyResponse])
def list_strategies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    strategies = get_user_strategies(db, current_user.id)
    return [
        StrategyResponse(
            id=strategy.id,
            user_id=strategy.user_id,
            name=strategy.name,
            description=strategy.description,
            rules_json=json.loads(strategy.rules_json),
            created_at=strategy.created_at,
        )
        for strategy in strategies
    ]


@router.post("/generate", response_model=StrategyAIResponse)
async def generate_strategy(
    request: StrategyGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not request.prompt:
        raise HTTPException(status_code=400, detail="A prompt is required for AI strategy generation.")

    ai_strategy = await generate_ai_strategy(db, current_user, request.prompt)
    if request.name:
        ai_strategy["name"] = request.name
    return StrategyAIResponse(**ai_strategy)
