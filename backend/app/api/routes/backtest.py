import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, get_db
from app.models.user import User
from app.schemas.backtest import BacktestRunCreate, BacktestRunResponse, BacktestOptimizeRequest, BacktestOptimizationResult
from app.services.backtesting_service import run_backtest, get_backtest_run, optimize_backtest

router = APIRouter(prefix="/backtest", tags=["Backtest"])


@router.post("/run", response_model=BacktestRunResponse)
def run_backtest_route(
    payload: BacktestRunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        backtest = run_backtest(
            db=db,
            user_id=current_user.id,
            strategy_id=payload.strategy_id,
            ticker=payload.ticker,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return BacktestRunResponse(
        id=backtest.id,
        strategy_id=backtest.strategy_id,
        ticker=backtest.ticker,
        start_date=backtest.start_date,
        end_date=backtest.end_date,
        results_json=json.loads(backtest.results_json),
        created_at=backtest.created_at,
    )


@router.get("/{run_id}", response_model=BacktestRunResponse)
def get_backtest_route(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    backtest = get_backtest_run(db, current_user.id, run_id)
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest run not found.")

    return BacktestRunResponse(
        id=backtest.id,
        strategy_id=backtest.strategy_id,
        ticker=backtest.ticker,
        start_date=backtest.start_date,
        end_date=backtest.end_date,
        results_json=json.loads(backtest.results_json),
        created_at=backtest.created_at,
    )


@router.post("/optimize", response_model=BacktestOptimizationResult)
def optimize_backtest_route(
    payload: BacktestOptimizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        optimization = optimize_backtest(
            db=db,
            user_id=current_user.id,
            strategy_id=payload.strategy_id,
            ticker=payload.ticker,
            start_date=payload.start_date,
            end_date=payload.end_date,
            parameter=payload.parameter,
            lower_bound=payload.lower_bound,
            upper_bound=payload.upper_bound,
            step=payload.step,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return BacktestOptimizationResult(**optimization)
