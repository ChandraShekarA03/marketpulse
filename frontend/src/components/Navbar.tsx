import Link from "next/link";
import { Activity, BarChart2, Briefcase, TrendingUp } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="glass sticky top-0 z-50 w-full border-b border-white/10 px-4 py-3 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold tracking-tighter text-white">
            MARKET<span className="text-primary">PULSE</span>
          </span>
        </div>
        
        <div className="hidden md:flex items-center gap-8">
          <Link href="/dashboard" className="text-sm font-medium text-slate-300 hover:text-white flex items-center gap-2 transition-colors">
            <BarChart2 className="h-4 w-4" /> Dashboard
          </Link>
          <Link href="/predictions" className="text-sm font-medium text-slate-300 hover:text-white flex items-center gap-2 transition-colors">
            <TrendingUp className="h-4 w-4" /> ML Predictions
          </Link>
          <Link href="/portfolio" className="text-sm font-medium text-slate-300 hover:text-white flex items-center gap-2 transition-colors">
            <Briefcase className="h-4 w-4" /> Portfolio
          </Link>
          <Link href="/research" className="text-sm font-medium text-slate-300 hover:text-white flex items-center gap-2 transition-colors">
            <BarChart2 className="h-4 w-4" /> Research
          </Link>
          <Link href="/ai-analyst" className="text-sm font-medium text-slate-300 hover:text-white flex items-center gap-2 transition-colors">
            <Activity className="h-4 w-4" /> AI Analyst
          </Link>
        </div>
        
        {/* Auth is temporarily disabled for future use
        <div className="flex items-center gap-4">
          <Link href="/login" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">
            Sign In
          </Link>
          <Link href="/register" className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 shadow-[0_0_15px_rgba(59,130,246,0.4)] transition-all">
            Get Started
          </Link>
        </div>
        */}
      </div>
    </nav>
  );
}
