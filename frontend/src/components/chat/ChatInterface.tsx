"use client";

import { useState, FormEvent } from 'react';
import RecommendationCard from './RecommendationCard';

export default function ChatInterface() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<{role: 'user' | 'agent', text: string, data?: any}[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!query.trim()) return;

    const prompt = query.trim();
    setMessages(prev => [...prev, { role: 'user', text: prompt }]);
    setLoading(true);
    setQuery("");

    const assistantIndex = messages.length;
    setMessages(prev => [...prev, { role: 'agent', text: 'Analyzing...', data: null }]);

    try {
      const response = await fetch('/api/v1/agent/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: prompt }),
      });

      if (!response.body) {
        throw new Error('No response stream available');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let partialText = '';
      let finalData: any = null;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const payload = JSON.parse(line);
            if (payload.type === 'partial') {
              partialText += payload.text;
              setMessages(prev => {
                const next = [...prev];
                next[assistantIndex] = { ...next[assistantIndex], text: partialText };
                return next;
              });
            }
            if (payload.type === 'final') {
              finalData = payload.payload;
              setMessages(prev => {
                const next = [...prev];
                next[assistantIndex] = {
                  ...next[assistantIndex],
                  text: partialText || `Analysis complete for ${finalData.symbol}`,
                  data: finalData,
                };
                return next;
              });
            }
            if (payload.type === 'error') {
              setMessages(prev => {
                const next = [...prev];
                next[assistantIndex] = { ...next[assistantIndex], text: `Agent error: ${payload.message}` };
                return next;
              });
            }
          } catch (err) {
            // Ignore partial parse errors until the full line is available.
          }
        }
      }

      if (!finalData) {
        setMessages(prev => {
          const next = [...prev];
          next[assistantIndex] = { ...next[assistantIndex], text: partialText || 'Unable to parse agent response.' };
          return next;
        });
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'agent', text: 'Error fetching recommendation.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 text-slate-100 rounded-xl overflow-hidden shadow-2xl border border-slate-800">
      <div className="flex-1 p-6 overflow-y-auto space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-slate-500">
            Ask me anything about the market. Try: "Should I buy AAPL today?"
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-2xl rounded-lg p-4 ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-800 border border-slate-700'}`}>
              <p>{msg.text}</p>
              {msg.data && (
                <div className="mt-4">
                  <RecommendationCard data={msg.data} />
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 flex space-x-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
            </div>
          </div>
        )}
      </div>

      <div className="p-4 bg-slate-950 border-t border-slate-800">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-slate-400"
            placeholder="E.g., Should I buy TSLA given the recent news?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 transition-colors px-6 py-3 rounded-lg font-medium text-white disabled:opacity-50"
          >
            Analyze
          </button>
        </form>
      </div>
    </div>
  );
}
