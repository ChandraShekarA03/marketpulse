"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";

type Holding = {
  id: number;
  ticker: string;
  shares: number;
  average_buy_price: number;
  current_price?: number;
  profit_loss?: number;
  current_value?: number;
  allocation_percentage?: number;
};

type Portfolio = {
  id: number;
  name: string;
  created_at: string;
  holdings: Holding[];
  total_value?: number;
  total_profit_loss?: number;
  risk_score?: number;
};

export default function PortfolioPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedPortfolio, setSelectedPortfolio] = useState<number | null>(null);
  const [holdingTicker, setHoldingTicker] = useState("");
  const [holdingShares, setHoldingShares] = useState(0);
  const [holdingPrice, setHoldingPrice] = useState(0);

  const token = typeof window !== "undefined" ? window.localStorage.getItem("token") : null;

  const fetchPortfolios = async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/portfolio");
      setPortfolios(response.data || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Unable to load portfolios.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolios();
  }, [token]);

  const createPortfolio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError("");
    setSuccess("");

    try {
      await api.post("/portfolio", { name: name.trim() });
      setName("");
      setSuccess("Portfolio created successfully.");
      fetchPortfolios();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create portfolio.");
    } finally {
      setLoading(false);
    }
  };

  const deletePortfolio = async (portfolioId: number) => {
    setLoading(true);
    setError("");
    try {
      await api.delete(`/portfolio/${portfolioId}`);
      setSuccess("Portfolio deleted.");
      setSelectedPortfolio((current) => (current === portfolioId ? null : current));
      fetchPortfolios();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Unable to delete portfolio.");
    } finally {
      setLoading(false);
    }
  };

  const addHolding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPortfolio) return;
    setLoading(true);
    setError("");
    setSuccess("");

    try {
      await api.post(`/portfolio/${selectedPortfolio}/holdings`, {
        ticker: holdingTicker.trim().toUpperCase(),
        shares: holdingShares,
        average_buy_price: holdingPrice,
      });
      setHoldingTicker("");
      setHoldingShares(0);
      setHoldingPrice(0);
      setSuccess("Holding added.");
      fetchPortfolios();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Unable to add holding.");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="space-y-6">
        <div className="glass-panel rounded-2xl p-8">
          <h1 className="text-3xl font-bold">Portfolio Manager</h1>
          <p className="mt-3 text-slate-400">Sign in first to view or manage your portfolios.</p>
          <div className="mt-6">
            <a href="/login" className="inline-flex items-center justify-center rounded-full bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-primary/90">
              Sign in to continue
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Portfolio Manager</h1>
          <p className="text-slate-400">Create, inspect, and manage your holdings with live market enrichment.</p>
        </div>
        <div className="rounded-3xl bg-slate-950/70 border border-white/10 p-4">
          <p className="text-sm text-slate-400">Protected portfolio actions require authentication. Use the login page if you have not already signed in.</p>
        </div>
      </div>

      {error && <div className="rounded-2xl bg-rose-500/10 border border-rose-500/20 p-4 text-rose-200">{error}</div>}
      {success && <div className="rounded-2xl bg-emerald-500/10 border border-emerald-500/20 p-4 text-emerald-200">{success}</div>}

      <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <section className="glass-panel rounded-3xl p-6">
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <h2 className="text-xl font-semibold">Your Portfolios</h2>
              <p className="text-sm text-slate-400">Select one to view holdings and add new positions.</p>
            </div>
          </div>

          {loading && portfolios.length === 0 ? (
            <div className="rounded-2xl border border-white/10 bg-slate-950 p-6 text-slate-400">Loading portfolios...</div>
          ) : portfolios.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950 p-6 text-slate-400">No portfolios yet. Create one to get started.</div>
          ) : (
            <div className="space-y-4">
              {portfolios.map((portfolio) => (
                <button
                  key={portfolio.id}
                  type="button"
                  onClick={() => setSelectedPortfolio(portfolio.id)}
                  className={`w-full rounded-3xl border p-4 text-left transition ${selectedPortfolio === portfolio.id ? "border-primary bg-primary/10" : "border-white/10 bg-slate-950/80 hover:border-white/20"}`}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-lg font-semibold">{portfolio.name}</p>
                      <p className="text-sm text-slate-500">Created: {new Date(portfolio.created_at).toLocaleDateString()}</p>
                    </div>
                    <span className="rounded-full bg-slate-800 px-3 py-1 text-xs uppercase tracking-[0.16em] text-slate-300">{portfolio.holdings.length} holdings</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="glass-panel rounded-3xl p-6">
          <h2 className="text-xl font-semibold mb-4">Create Portfolio</h2>
          <form onSubmit={createPortfolio} className="space-y-4">
            <label className="block text-sm font-medium text-slate-300">Portfolio Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="glass-input w-full rounded-2xl px-4 py-3"
              placeholder="Growth thesis"
              required
            />
            <button type="submit" disabled={loading} className="inline-flex items-center justify-center rounded-full bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-primary/90">
              {loading ? "Saving..." : "Create Portfolio"}
            </button>
          </form>
        </section>
      </div>

      {selectedPortfolio && (
        <section className="glass-panel rounded-3xl p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-xl font-semibold">Portfolio Details</h2>
              <p className="text-slate-400">Inspect holdings and add positions for the selected portfolio.</p>
            </div>
            <button
              type="button"
              onClick={() => deletePortfolio(selectedPortfolio)}
              className="rounded-full border border-rose-500/20 bg-rose-500/10 px-4 py-2 text-sm text-rose-200 hover:bg-rose-500/20"
            >
              Delete portfolio
            </button>
          </div>

          {portfolios
            .filter((portfolio) => portfolio.id === selectedPortfolio)
            .map((portfolio) => (
              <div key={portfolio.id} className="mt-6 space-y-6">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-4">
                    <p className="text-sm text-slate-400">Total Value</p>
                    <p className="mt-2 text-2xl font-semibold text-white">${portfolio.total_value?.toFixed(2) ?? "0.00"}</p>
                  </div>
                  <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-4">
                    <p className="text-sm text-slate-400">Profit / Loss</p>
                    <p className={`mt-2 text-2xl font-semibold ${portfolio.total_profit_loss && portfolio.total_profit_loss >= 0 ? "text-bullish" : "text-bearish"}`}>
                      {portfolio.total_profit_loss !== undefined ? `$${portfolio.total_profit_loss.toFixed(2)}` : "$0.00"}
                    </p>
                  </div>
                  <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-4">
                    <p className="text-sm text-slate-400">Risk Score</p>
                    <p className="mt-2 text-2xl font-semibold text-white">{portfolio.risk_score ?? 0}%</p>
                  </div>
                </div>

                <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-6">
                  <h3 className="mb-4 text-lg font-semibold">Holdings</h3>
                  {portfolio.holdings.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-white/10 bg-slate-900/80 p-6 text-slate-400">No holdings yet. Add one below to begin tracking live data.</div>
                  ) : (
                    <div className="space-y-4">
                      {portfolio.holdings.map((holding) => (
                        <div key={holding.id} className="grid gap-4 rounded-3xl border border-white/10 bg-slate-950/90 p-4 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
                          <div>
                            <p className="font-semibold text-white">{holding.ticker}</p>
                            <p className="text-sm text-slate-500">Shares: {holding.shares}</p>
                          </div>
                          <div>
                            <p className="text-sm text-slate-400">Avg Cost</p>
                            <p className="font-semibold text-white">${holding.average_buy_price.toFixed(2)}</p>
                          </div>
                          <div>
                            <p className="text-sm text-slate-400">Current Price</p>
                            <p className="font-semibold text-white">{holding.current_price !== undefined ? `$${holding.current_price.toFixed(2)}` : "--"}</p>
                          </div>
                          <div>
                            <p className="text-sm text-slate-400">PnL</p>
                            <p className={`font-semibold ${holding.profit_loss && holding.profit_loss >= 0 ? "text-bullish" : "text-bearish"}`}>
                              {holding.profit_loss !== undefined ? `$${holding.profit_loss.toFixed(2)}` : "$0.00"}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-6">
                  <h3 className="mb-4 text-lg font-semibold">Add New Holding</h3>
                  <form onSubmit={addHolding} className="grid gap-4 sm:grid-cols-2">
                    <label className="space-y-2">
                      <span className="text-sm text-slate-300">Ticker</span>
                      <input
                        value={holdingTicker}
                        onChange={(e) => setHoldingTicker(e.target.value.toUpperCase())}
                        className="glass-input w-full rounded-2xl px-4 py-3"
                        placeholder="AAPL"
                        required
                      />
                    </label>
                    <label className="space-y-2">
                      <span className="text-sm text-slate-300">Shares</span>
                      <input
                        type="number"
                        step="0.01"
                        value={holdingShares}
                        onChange={(e) => setHoldingShares(Number(e.target.value))}
                        className="glass-input w-full rounded-2xl px-4 py-3"
                        placeholder="10"
                        required
                      />
                    </label>
                    <label className="space-y-2 sm:col-span-2">
                      <span className="text-sm text-slate-300">Average Buy Price</span>
                      <input
                        type="number"
                        step="0.01"
                        value={holdingPrice}
                        onChange={(e) => setHoldingPrice(Number(e.target.value))}
                        className="glass-input w-full rounded-2xl px-4 py-3"
                        placeholder="145.00"
                        required
                      />
                    </label>
                    <button type="submit" disabled={loading} className="rounded-full bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-primary/90 sm:col-span-2">
                      {loading ? "Adding..." : "Add Holding"}
                    </button>
                  </form>
                </div>
              </div>
            ))}
        </section>
      )}
    </div>
  );
}
