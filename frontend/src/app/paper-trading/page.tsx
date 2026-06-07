"use client";
import { useState, useEffect } from "react";
import { Activity } from "lucide-react";

export default function PaperTradingPage() {
  const [wsStatus, setWsStatus] = useState("Disconnected");
  const [updates, setUpdates] = useState<any[]>([]);
  const ticker = "AAPL"; // Example ticker

  useEffect(() => {
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
          setUpdates((prev) => [data, ...prev].slice(0, 50));
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
      <h1 className="text-3xl font-bold">Paper Trading Live Stream</h1>
      <div className="glass-panel rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Activity className={`h-5 w-5 ${wsStatus === 'Connected' ? 'text-green-500' : 'text-yellow-500'}`} />
          <span>WebSocket: {wsStatus}</span>
        </div>
        <div className="h-64 overflow-y-auto bg-black/20 p-4 rounded text-sm font-mono space-y-2">
          {updates.length === 0 && <p className="text-slate-500">Waiting for updates...</p>}
          {updates.map((upd, idx) => (
            <div key={idx} className="border-b border-white/5 pb-1">
              <span className="text-slate-400">[{new Date().toLocaleTimeString()}]</span> {JSON.stringify(upd)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
