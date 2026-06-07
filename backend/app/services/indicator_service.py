import pandas as pd
import numpy as np
import ta
from fastapi import HTTPException
from app.services.stock_service import get_historical_data
from app.schemas.indicator import IndicatorValues
import logging

logger = logging.getLogger(__name__)

def generate_indicators(ticker: str) -> dict:
    """
    Generate technical indicators for a given stock using pandas and the `ta` library.
    """
    try:
        # Fetch historical data
        raw_data = get_historical_data(ticker, outputsize="compact")
        
        # Convert to DataFrame
        df = pd.DataFrame(raw_data)
        
        if len(df) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough historical data for {ticker} to compute indicators."
            )
            
        # Ensure correct types
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['volume'] = pd.to_numeric(df['volume'])
        
        # Calculate Indicators
        # RSI
        df['RSI'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
        
        # MACD
        macd = ta.trend.MACD(close=df['close'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        df['MACD_hist'] = macd.macd_diff()
        
        # SMA 20
        df['SMA20'] = ta.trend.SMAIndicator(close=df['close'], window=20).sma_indicator()
        
        # EMA 50
        df['EMA50'] = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
        df['BB_high'] = bb.bollinger_hband()
        df['BB_low'] = bb.bollinger_lband()
        
        # ATR
        df['ATR'] = ta.volatility.AverageTrueRange(
            high=df['high'], low=df['low'], close=df['close'], window=14
        ).average_true_range()
        
        # Stochastic Oscillator
        stoch = ta.momentum.StochasticOscillator(
            high=df['high'], low=df['low'], close=df['close'], window=14, smooth_window=3
        )
        df['Stochastic_k'] = stoch.stoch()
        df['Stochastic_d'] = stoch.stoch_signal()
        
        # Get the latest row (drop nan values for safe extraction)
        latest = df.iloc[-1]
        
        # Formulate trend and signals
        rsi = latest['RSI']
        macd_val = latest['MACD']
        macd_signal = latest['MACD_signal']
        close_price = latest['close']
        sma20 = latest['SMA20']
        
        trend = "NEUTRAL"
        if close_price > sma20 and macd_val > macd_signal:
            trend = "BULLISH"
        elif close_price < sma20 and macd_val < macd_signal:
            trend = "BEARISH"
            
        signal = "HOLD"
        if rsi < 30 and trend == "BULLISH":
            signal = "BUY"
        elif rsi > 70 and trend == "BEARISH":
            signal = "SELL"
        
        # Clean up numpy nans
        def clean_val(v):
            return None if pd.isna(v) else float(v)

        indicators = IndicatorValues(
            RSI=clean_val(latest['RSI']),
            MACD=clean_val(latest['MACD']),
            MACD_signal=clean_val(latest['MACD_signal']),
            MACD_hist=clean_val(latest['MACD_hist']),
            SMA20=clean_val(latest['SMA20']),
            EMA50=clean_val(latest['EMA50']),
            BB_high=clean_val(latest['BB_high']),
            BB_low=clean_val(latest['BB_low']),
            ATR=clean_val(latest['ATR']),
            Stochastic_k=clean_val(latest['Stochastic_k']),
            Stochastic_d=clean_val(latest['Stochastic_d'])
        )

        return {
            "ticker": ticker.upper(),
            "latest_close": clean_val(latest['close']),
            "indicators": indicators,
            "trend": trend,
            "signal": signal
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing indicators for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to compute technical indicators.")