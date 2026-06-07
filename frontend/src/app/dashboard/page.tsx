"use client";
import { useState, useEffect } from "react";
import { Search, TrendingUp, TrendingDown, Activity, BrainCircuit } from "lucide-react";
import api from "@/lib/api";

export default function DashboardPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [stockData, setStockData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [predictionData, setPredictionData] = useState<any>(null);
  const [indicatorData, setIndicatorData] = useState<any>(null);
  const [sentimentData, setSentimentData] = useState<any>(null);

  const [wsStatus, setWsStatus] = useState("Disconnected");

  const searchStock = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      // Fetch core stock data
      const res = await api.get(`/stocks/${ticker}`);
      setStockData(res.data);
      
      // Fetch ML Predictions (Using Random Forest as default consensus)
      const predRes = await api.get(`/predict/${ticker}?model=randomforest`);
      setPredictionData(predRes.data);
      
      // Fetch Indicators
      const indRes = await api.get(`/indicators/${ticker}`);
      setIndicatorData(indRes.data);
      
      // Fetch Sentiment
      const sentRes = await api.get(`/sentiment/${ticker}`);
      setSentimentData(sentRes.data);
      
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch stock data from backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    searchStock({ preventDefault: () => {} } as React.FormEvent);
    
    let ws: WebSocket;
    let reconnectInterval: NodeJS.Timeout;

    const connectWs = () => {
      setWsStatus("Connecting...");
      ws = new WebSocket(`ws://localhost:8000/ws/stocks/${ticker}`);

      ws.onopen = () => {
        setWsStatus("Connected");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === "price_update" && data.price) {
            setStockData((prev: any) => prev ? { ...prev, price: data.price } : prev);
          }
        } catch (e) {
          console.error("WS parse error", e);
        }
      };

      ws.onclose = () => {
        setWsStatus("Disconnected");
        reconnectInterval = setTimeout(connectWs, 3000);
      };

      ws.onerror = () => {
        setWsStatus("Error");
        ws.close();
      };
    };

    connectWs();

    return () => {
      clearTimeout(reconnectInterval);
      if (ws) ws.close();
    };
  }, [ticker]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold">Market Dashboard</h1>
          <p className="text-slate-400">Real-time intelligence and automated analysis.</p>
        </div>
        
        <form onSubmit={searchStock} className="flex w-full md:w-auto relative">
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="Search ticker (e.g. AAPL)"
            className="glass-input rounded-l-lg px-4 py-2 w-full md:w-64"
            required
          />
          <button type="submit" className="bg-primary hover:bg-primary/90 text-white px-4 py-2 rounded-r-lg transition-colors flex items-center justify-center" disabled={loading}>
            {loading ? <Activity className="h-5 w-5 animate-spin" /> : <Search className="h-5 w-5" />}
          </button>
        </form>
      </div>

      {error && (
        <div className="bg-destructive/20 border border-destructive text-destructive px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {stockData && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Chart Area */}
          <div className="lg:col-span-2 space-y-6">
            <div className="glass-panel rounded-xl p-6 h-[400px] flex flex-col">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-2xl font-bold flex items-center gap-2">{stockData.symbol}</h2>
                  <div className="flex items-end gap-2 mt-1">
                    <span className="text-4xl font-extrabold">${stockData.price}</span>
                    <span className="text-bullish flex items-center font-medium mb-1">
                      <TrendingUp className="h-4 w-4 mr-1" /> +1.24%
                    </span>
                  </div>
                </div>
                <div className="text-right text-sm text-slate-400 space-y-1">
                  <p>Open: <span className="text-white">${stockData.open}</span></p>
                  <p>High: <span className="text-white">${stockData.high}</span></p>
                  <p>Low: <span className="text-white">${stockData.low}</span></p>
                  <p>Vol: <span className="text-white">{stockData.volume.toLocaleString()}</span></p>
                </div>
              </div>
              <div className="flex-1 border border-white/5 rounded-lg bg-black/20 flex items-center justify-center relative overflow-hidden group">
                <div className="absolute inset-0 bg-[url('https://www.tradingview.com/x/dummy')] bg-cover opacity-30 group-hover:opacity-40 transition-opacity"></div>
                <div className="text-slate-500 z-10 flex flex-col items-center gap-2">
                  <div className="flex items-center gap-2">
                    <Activity className={`h-5 w-5 ${wsStatus === 'Connected' ? 'text-green-500' : 'text-yellow-500'}`} />
                    <span>WebSocket: {wsStatus}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Prediction Panel */}
            <div className="glass-panel rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4 border-b border-white/10 pb-4">
                <BrainCircuit className="h-6 w-6 text-accent" />
                <h3 className="text-xl font-bold">AI Prediction Center</h3>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="glass rounded-lg p-4 text-center">
                  <p className="text-sm text-slate-400 mb-1">Target Price</p>
                  <p className={`text-lg font-bold ${predictionData?.trend === 'BULLISH' ? 'text-bullish' : 'text-bearish'}`}>
                    ${predictionData?.predicted_next_day?.toFixed(2) || '---'}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Conf: {predictionData?.confidence_score || '---'}%</p>
                </div>
                <div className="glass rounded-lg p-4 text-center">
                  <p className="text-sm text-slate-400 mb-1">Model</p>
                  <p className="text-lg font-bold text-white uppercase">{predictionData?.model || '---'}</p>
                  <p className="text-xs text-slate-500 mt-1">R2: {predictionData?.evaluation_metrics?.R2?.toFixed(2) || '---'}</p>
                </div>
                <div className="glass rounded-lg p-4 text-center">
                  <p className="text-sm text-slate-400 mb-1">MSE Error</p>
                  <p className="text-lg font-bold text-white">{predictionData?.evaluation_metrics?.MSE?.toFixed(2) || '---'}</p>
                  <p className="text-xs text-slate-500 mt-1">RMSE: {predictionData?.evaluation_metrics?.RMSE?.toFixed(2) || '---'}</p>
                </div>
                <div className="glass rounded-lg p-4 text-center bg-primary/10 border-primary/30">
                  <p className="text-sm text-primary mb-1 font-medium">Consensus</p>
                  <p className={`text-xl font-bold ${predictionData?.trend === 'BULLISH' ? 'text-bullish' : 'text-bearish'}`}>
                    {predictionData?.trend || 'WAITING'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar Area */}
          <div className="space-y-6">
            {/* Sentiment Gauge */}
            <div className="glass-panel rounded-xl p-6">
              <h3 className="text-lg font-bold mb-4">FinBERT Sentiment</h3>
              <div className="relative h-40 flex items-center justify-center">
                {/* Simulated Half-donut gauge */}
                <div className="absolute w-40 h-20 bg-gradient-to-r from-bearish via-neutral to-bullish rounded-t-full border-b-0 overflow-hidden" style={{ top: '20px'}}></div>
                <div className="absolute w-32 h-16 bg-slate-900 rounded-t-full border-b-0" style={{ top: '36px'}}></div>
                <div className="absolute w-1 h-24 bg-white origin-bottom transform rotate-45 rounded-full" style={{ top: '16px'}}></div>
                <div className="absolute bottom-0 text-center">
                  <p className={`text-2xl font-black ${sentimentData?.market_sentiment === 'BULLISH' ? 'text-bullish' : sentimentData?.market_sentiment === 'BEARISH' ? 'text-bearish' : 'text-neutral'}`}>
                    {sentimentData?.market_sentiment || 'UNKNOWN'}
                  </p>
                  <p className="text-xs text-slate-400">Based on {sentimentData?.articles_analyzed || 0} recent articles</p>
                </div>
              </div>
            </div>

            {/* Technical Indicators */}
            <div className="glass-panel rounded-xl p-6">
              <h3 className="text-lg font-bold mb-4">Technical Indicators</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center pb-2 border-b border-white/5">
                  <span className="text-slate-400">RSI (14)</span>
                  <span className="font-bold">{indicatorData?.indicators?.RSI?.toFixed(2) || '---'}</span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b border-white/5">
                  <span className="text-slate-400">MACD</span>
                  <span className="font-bold">{indicatorData?.indicators?.MACD?.toFixed(2) || '---'}</span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b border-white/5">
                  <span className="text-slate-400">SMA (20)</span>
                  <span className="font-bold">{indicatorData?.indicators?.SMA20?.toFixed(2) || '---'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Signal</span>
                  <span className={`font-bold ${indicatorData?.signal === 'BUY' ? 'text-bullish' : indicatorData?.signal === 'SELL' ? 'text-bearish' : 'text-neutral'}`}>
                    {indicatorData?.signal || '---'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
