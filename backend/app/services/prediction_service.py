import pandas as pd
import numpy as np
import ta
import logging
from fastapi import HTTPException
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
import xgboost as xgb

# Only import tensorflow if available and avoid allocating all GPU memory
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

from app.services.stock_service import get_historical_data
from app.services.cache_service import cache_response

logger = logging.getLogger(__name__)

def prepare_features(ticker: str) -> pd.DataFrame:
    """
    Fetch data and engineer features: Lag1, Lag2, Lag3, RSI, MACD, SMA20, EMA50, Volume, Volatility.
    """
    raw_data = get_historical_data(ticker, outputsize="full")
    df = pd.DataFrame(raw_data)
    
    if len(df) < 100:
        raise HTTPException(status_code=400, detail="Not enough data for ML prediction.")
        
    df['close'] = pd.to_numeric(df['close'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['volume'] = pd.to_numeric(df['volume'])
    
    # Target variable: next day's close price
    df['target'] = df['close'].shift(-1)
    
    # Feature Engineering
    df['Lag1'] = df['close'].shift(1)
    df['Lag2'] = df['close'].shift(2)
    df['Lag3'] = df['close'].shift(3)
    
    df['RSI'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['close'])
    df['MACD'] = macd.macd()
    
    df['SMA20'] = ta.trend.SMAIndicator(close=df['close'], window=20).sma_indicator()
    df['EMA50'] = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator()
    
    # Volatility approximation using ATR
    df['Volatility'] = ta.volatility.AverageTrueRange(
        high=df['high'], low=df['low'], close=df['close'], window=14
    ).average_true_range()
    
    # Drop rows with NaN values resulting from shifts and indicators
    df.dropna(inplace=True)
    return df

def calculate_metrics(y_true, y_pred) -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    return {"MAE": mae, "MSE": mse, "RMSE": rmse, "R2": r2}

def predict_traditional(df: pd.DataFrame, model_type: str) -> dict:
    features = ['Lag1', 'Lag2', 'Lag3', 'RSI', 'MACD', 'SMA20', 'EMA50', 'volume', 'Volatility']
    X = df[features]
    y = df['target']
    
    # Sequential split for time series
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    if model_type == 'linear':
        model = LinearRegression()
    elif model_type == 'randomforest':
        model = RandomForestRegressor(n_estimators=100, random_state=42)
    elif model_type == 'xgboost':
        model = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
    else:
        raise ValueError("Unsupported traditional model type")
        
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    metrics = calculate_metrics(y_test, predictions)
    
    # Predict next day using the very last row's data
    latest_features = df.iloc[-1][features].values.reshape(1, -1)
    next_day_pred = float(model.predict(latest_features)[0])
    
    return next_day_pred, metrics

def predict_lstm(df: pd.DataFrame) -> dict:
    if not TF_AVAILABLE:
        raise HTTPException(status_code=500, detail="TensorFlow is not available for LSTM models.")
        
    features = ['Lag1', 'Lag2', 'Lag3', 'RSI', 'MACD', 'SMA20', 'EMA50', 'volume', 'Volatility']
    
    # Scale data
    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()
    
    X_scaled = scaler_X.fit_transform(df[features])
    y_scaled = scaler_y.fit_transform(df[['target']])
    
    # Create sequences (e.g., 10 days window)
    window_size = 10
    X_seq, y_seq = [], []
    for i in range(len(X_scaled) - window_size):
        X_seq.append(X_scaled[i:(i + window_size)])
        y_seq.append(y_scaled[i + window_size])
        
    X_seq = np.array(X_seq)
    y_seq = np.array(y_seq)
    
    split = int(len(X_seq) * 0.8)
    X_train, X_test = X_seq[:split], X_seq[split:]
    y_train, y_test = y_seq[:split], y_seq[split:]
    
    # Build LSTM
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=(window_size, len(features))),
        Dropout(0.2),
        LSTM(50, return_sequences=False),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    
    early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
    model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=20, batch_size=32, verbose=0, callbacks=[early_stop])
    
    y_pred_scaled = model.predict(X_test, verbose=0)
    y_pred = scaler_y.inverse_transform(y_pred_scaled).flatten()
    y_test_orig = scaler_y.inverse_transform(y_test).flatten()
    
    metrics = calculate_metrics(y_test_orig, y_pred)
    
    # Predict next day
    latest_seq = X_scaled[-window_size:].reshape(1, window_size, len(features))
    next_pred_scaled = model.predict(latest_seq, verbose=0)
    next_day_pred = float(scaler_y.inverse_transform(next_pred_scaled)[0][0])
    
    return next_day_pred, metrics

@cache_response(ttl_seconds=3600) # Cache predictions for 1 hour to save compute
def run_prediction(ticker: str, model_type: str) -> dict:
    """
    Run the multi-model ML engine for a specific ticker and model.
    """
    model_type = model_type.lower()
    valid_models = ['linear', 'randomforest', 'xgboost', 'lstm']
    
    if model_type not in valid_models:
        raise HTTPException(status_code=400, detail=f"Invalid model. Choose from: {valid_models}")
        
    try:
        df = prepare_features(ticker)
        today_price = float(df.iloc[-1]['close'])
        
        if model_type == 'lstm':
            next_day_pred, metrics = predict_lstm(df)
        else:
            next_day_pred, metrics = predict_traditional(df, model_type)
            
        trend = "BULLISH" if next_day_pred > today_price else "BEARISH"
        
        # Confidence score heuristic (based on R2 and relative distance)
        r2_weight = max(0, min(1, metrics['R2']))
        confidence = round(r2_weight * 100, 2)
        
        return {
            "ticker": ticker.upper(),
            "model": model_type,
            "today_price": today_price,
            "predicted_next_day": next_day_pred,
            "trend": trend,
            "confidence_score": confidence,
            "evaluation_metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Prediction error for {ticker} using {model_type}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")