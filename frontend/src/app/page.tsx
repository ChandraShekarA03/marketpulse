import Link from "next/link";
import { ArrowRight, BarChart2, BrainCircuit, ShieldAlert } from "lucide-react";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] text-center space-y-12">
      {/* Hero Section */}
      <div className="space-y-6 max-w-4xl relative">
        <div className="absolute -top-24 -left-24 w-64 h-64 bg-primary/20 rounded-full blur-[100px] -z-10"></div>
        <div className="absolute -bottom-24 -right-24 w-64 h-64 bg-accent/20 rounded-full blur-[100px] -z-10"></div>
        
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-white">
          The Future of <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent">Market Intelligence</span>
        </h1>
        <p className="text-xl text-slate-300 max-w-2xl mx-auto">
          Unleash the power of AI to analyze stocks, predict trends, and manage your portfolio with institutional-grade tools built for retail investors.
        </p>
        <div className="flex justify-center gap-4 pt-4">
          {/* Auth is temporarily disabled
          <Link href="/register" className="flex items-center gap-2 rounded-xl bg-primary px-8 py-4 text-lg font-bold text-white hover:bg-primary/90 shadow-[0_0_30px_rgba(59,130,246,0.5)] transition-all transform hover:scale-105">
            Start Trading Smart <ArrowRight className="h-5 w-5" />
          </Link>
          */}
          <Link href="/dashboard" className="flex items-center gap-2 rounded-xl glass px-8 py-4 text-lg font-bold text-white hover:bg-white/5 transition-all">
            View Live Demo
          </Link>
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full pt-16">
        <div className="glass-panel p-8 rounded-2xl text-left space-y-4 hover:border-primary/50 transition-colors">
          <div className="h-12 w-12 rounded-lg bg-primary/20 flex items-center justify-center text-primary mb-6">
            <BarChart2 className="h-6 w-6" />
          </div>
          <h3 className="text-xl font-bold text-white">Technical Analysis</h3>
          <p className="text-slate-400">Live streaming data with 15+ automated technical indicators to identify precise entry and exit points.</p>
        </div>
        
        <div className="glass-panel p-8 rounded-2xl text-left space-y-4 hover:border-accent/50 transition-colors">
          <div className="h-12 w-12 rounded-lg bg-accent/20 flex items-center justify-center text-accent mb-6">
            <BrainCircuit className="h-6 w-6" />
          </div>
          <h3 className="text-xl font-bold text-white">Multi-Model AI</h3>
          <p className="text-slate-400">Leverage XGBoost, Random Forest, and LSTM neural networks to predict next-day price movements.</p>
        </div>
        
        <div className="glass-panel p-8 rounded-2xl text-left space-y-4 hover:border-bullish/50 transition-colors">
          <div className="h-12 w-12 rounded-lg bg-bullish/20 flex items-center justify-center text-bullish mb-6">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <h3 className="text-xl font-bold text-white">Risk Management</h3>
          <p className="text-slate-400">Automated portfolio tracking, real-time PnL, and live FinBERT sentiment analysis on market news.</p>
        </div>
      </div>
    </div>
  );
}
