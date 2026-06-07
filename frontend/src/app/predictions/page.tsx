"use client";

import { useState } from "react";
import api from "@/lib/api";

export default function PredictionsPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [model, setModel] = useState("randomforest");
  const [prediction, setPrediction] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchPrediction = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setPrediction(null);

    try {
      const response = await api.get(`/predict/${ticker}`, {
        params: { model },
      });
      setPrediction(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch prediction.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">ML Predictions</h1>
          <p className="text-slate-400">Run a prediction and review model metrics for any ticker.</p>
        </div>
      </div>

      <div className="glass-panel rounded-3xl p-6">
        <form onSubmit={fetchPrediction} className="grid gap-4 md:grid-cols-3">
          <label className="space-y-2">
            <span className="text-sm text-slate-300">Ticker</span>
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="glass-input w-full rounded-2xl px-4 py-3"
              placeholder="AAPL"
              required
            />
          </label>

          <label className="space-y-2">
            <span className="text-sm text-slate-300">Model</span>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="glass-input w-full rounded-2xl px-4 py-3"
            >
              <option value="linear">Linear Regression</option>
              <option value="randomforest">Random Forest</option>
              <option value="xgboost">XGBoost</option>
              <option value="lstm">LSTM</option>
            </select>
          </label>

          <button type="submit" disabled={loading} className="rounded-full bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-primary/90">
            {loading ? "Predicting..." : "Run Prediction"}
          </button>
        </form>
      </div>

      {error && <div className="rounded-3xl bg-rose-500/10 border border-rose-500/20 p-4 text-rose-100">{error}</div>}

      {prediction ? (
        <div className="glass-panel rounded-3xl p-6 space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-5">
              <p className="text-sm text-slate-400">Ticker</p>
              <p className="mt-2 text-3xl font-semibold text-white">{prediction.ticker}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-5">
              <p className="text-sm text-slate-400">Model</p>
              <p className="mt-2 text-3xl font-semibold text-white uppercase">{prediction.model}</p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-5">
              <p className="text-sm text-slate-400">Predicted Next Day</p>
              <p className="mt-2 text-2xl font-semibold text-white">${prediction.predicted_next_day?.toFixed(2)}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-5">
              <p className="text-sm text-slate-400">Trend</p>
              <p className={`mt-2 text-2xl font-semibold ${prediction.trend === 'BULLISH' ? 'text-bullish' : 'text-bearish'}`}>{prediction.trend}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-5">
              <p className="text-sm text-slate-400">Confidence</p>
              <p className="mt-2 text-2xl font-semibold text-white">{prediction.confidence_score}%</p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-5">
              <p className="text-sm text-slate-400">MAE</p>
              <p className="mt-2 text-xl font-semibold text-white">{prediction.evaluation_metrics.MAE.toFixed(4)}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-5">
              <p className="text-sm text-slate-400">MSE</p>
              <p className="mt-2 text-xl font-semibold text-white">{prediction.evaluation_metrics.MSE.toFixed(4)}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-5">
              <p className="text-sm text-slate-400">RMSE</p>
              <p className="mt-2 text-xl font-semibold text-white">{prediction.evaluation_metrics.RMSE.toFixed(4)}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-5">
              <p className="text-sm text-slate-400">R²</p>
              <p className="mt-2 text-xl font-semibold text-white">{prediction.evaluation_metrics.R2.toFixed(4)}</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-3xl border border-dashed border-white/10 bg-slate-950/80 p-6 text-slate-400">No prediction yet. Enter a ticker and run the model.</div>
      )}
    </div>
  );
}
