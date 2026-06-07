"use client";

import { useState, FormEvent } from 'react';
import api from '@/lib/api';

interface SourceItem {
  source_url: string;
  filing_type: string;
  filing_date: string;
}

export default function ResearchCopilot() {
  const [ticker, setTicker] = useState('');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [citations, setCitations] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!ticker.trim() || !question.trim()) {
      setError('Ticker and question are required.');
      return;
    }
    setLoading(true);
    setError('');
    setAnswer('');
    setSources([]);
    setCitations([]);

    try {
      const response = await api.post('/rag/query', {
        ticker: ticker.trim().toUpperCase(),
        question: question.trim(),
      });

      setAnswer(response.data.answer);
      setSources(response.data.sources || []);
      setCitations(response.data.citations || []);
    } catch (err) {
      setError('Unable to fetch research results. Try ingesting filings first or validate your token.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 rounded-3xl border border-slate-800 shadow-2xl overflow-hidden">
      <div className="p-6 border-b border-slate-800 bg-slate-900">
        <h2 className="text-2xl font-bold text-white">Institutional Research Copilot</h2>
        <p className="text-slate-400 mt-2 max-w-2xl">
          Ask deep questions about SEC filings, annual reports, quarterly reports, 8-Ks, and corporate disclosures.
          Responses are grounded in the latest ingested filing excerpts with citation markers.
        </p>
      </div>

      <div className="p-6 space-y-6 overflow-y-auto flex-1">
        <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-[220px_minmax(0,1fr)]">
          <div>
            <label className="text-sm font-semibold text-slate-300">Ticker</label>
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="NVDA"
            />
          </div>
          <div className="md:col-span-1 md:flex md:flex-col">
            <label className="text-sm font-semibold text-slate-300">Question</label>
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="What risks does NVIDIA mention regarding competition?"
            />
          </div>
          <div className="md:col-span-2 flex items-end">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
            >
              {loading ? 'Searching filings...' : 'Ask Research Copilot'}
            </button>
          </div>
        </form>

        {error && (
          <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200">
            {error}
          </div>
        )}

        {answer && (
          <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6">
            <h3 className="text-xl font-semibold text-white">Grounded Answer</h3>
            <p className="mt-4 whitespace-pre-wrap text-slate-200">{answer}</p>
          </section>
        )}

        {sources.length > 0 && (
          <section className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Sources</h3>
            <div className="grid gap-4 md:grid-cols-2">
              {sources.map((source) => (
                <div key={source.source_url} className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                  <p className="text-sm text-slate-400">{source.filing_type} · {source.filing_date}</p>
                  <a href={source.source_url} target="_blank" rel="noreferrer" className="mt-2 block text-sm font-medium text-blue-400 hover:text-blue-300 break-all">
                    {source.source_url}
                  </a>
                </div>
              ))}
            </div>
          </section>
        )}

        {citations.length > 0 && (
          <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6">
            <h3 className="text-lg font-semibold text-white">Citations</h3>
            <ul className="mt-4 space-y-2 text-slate-300">
              {citations.map((citation) => (
                <li key={citation} className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3">
                  {citation}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}
