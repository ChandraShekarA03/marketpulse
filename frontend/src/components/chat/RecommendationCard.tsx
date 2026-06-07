export default function RecommendationCard({ data }: { data: any }) {
  const getRecommendationColor = (rec: string) => {
    switch (rec?.toUpperCase()) {
      case 'BUY': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'SELL': return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      default: return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    }
  };

  const colorClass = getRecommendationColor(data.recommendation);

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden w-full max-w-lg shadow-xl">
      <div className="p-5 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
        <div>
          <h3 className="text-2xl font-bold text-white tracking-tight">{data.symbol}</h3>
          <p className="text-sm text-slate-400 font-medium mt-1">AI Analysis Result</p>
        </div>
        <div className={`px-4 py-2 rounded-lg border font-bold text-lg tracking-wide ${colorClass}`}>
          {data.recommendation}
        </div>
      </div>
      
      <div className="p-5 space-y-5">
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm font-medium">Confidence Score</span>
          <div className="flex items-center gap-3">
            <div className="w-32 h-2 bg-slate-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-blue-500 rounded-full transition-all duration-1000"
                style={{ width: `${data.confidence}%` }}
              />
            </div>
            <span className="text-white font-bold text-lg">{data.confidence}%</span>
          </div>
        </div>

        <div className="space-y-3">
          <span className="text-slate-400 text-sm font-medium">Key Reasoning</span>
          <ul className="space-y-2">
            {data.reasoning?.map((reason: string, idx: number) => (
              <li key={idx} className="flex items-start gap-2 text-slate-300">
                <span className="text-blue-500 mt-1">•</span>
                <span className="leading-relaxed">{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
