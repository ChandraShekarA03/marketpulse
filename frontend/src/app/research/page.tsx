import ResearchCopilot from '@/components/research/ResearchCopilot';

export const metadata = {
  title: 'Research Copilot - MarketPulse',
  description: 'Ask questions about SEC filings, earnings reports, and corporate disclosures.',
};

export default function ResearchPage() {
  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-7xl mx-auto p-4 md:p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight text-white">Research Copilot</h1>
        <p className="text-slate-400 mt-2">
          Query company filings and corporate disclosures with grounded answers and citation-aware sources.
        </p>
      </div>
      <div className="flex-1 min-h-0">
        <ResearchCopilot />
      </div>
    </div>
  );
}
