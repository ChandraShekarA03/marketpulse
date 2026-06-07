import ChatInterface from '@/components/chat/ChatInterface';

export const metadata = {
  title: 'AI Analyst - MarketPulse',
  description: 'Interact with the autonomous AI financial analyst.',
};

export default function AIAnalystPage() {
  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-6xl mx-auto p-4 md:p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight text-white">Agentic AI Analyst</h1>
        <p className="text-slate-400 mt-2">
          Ask the AI to analyze stocks. It will autonomously query technical indicators, machine learning predictions, and market sentiment to provide a comprehensive recommendation.
        </p>
      </div>
      
      <div className="flex-1 min-h-0">
        <ChatInterface />
      </div>
    </div>
  );
}
