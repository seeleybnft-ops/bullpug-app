/**
 * InsightsSection - AI-generated trading insights
 * Extracted from JournalAIAssistant for better maintainability
 */

import { RefreshCw } from "lucide-react";
import ReactMarkdown from "react-markdown";

export default function InsightsSection({ 
  insights, 
  loading, 
  onRefresh 
}) {
  return (
    <div data-testid="insights-section">
      <div className="flex justify-end mb-3">
        <button 
          onClick={onRefresh}
          disabled={loading}
          className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
          data-testid="refresh-insights-btn"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>
      {loading ? (
        <div className="space-y-3">
          <div className="h-4 bg-white/10 rounded animate-pulse w-3/4" />
          <div className="h-4 bg-white/10 rounded animate-pulse w-full" />
          <div className="h-4 bg-white/10 rounded animate-pulse w-5/6" />
        </div>
      ) : (
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="text-slate-300 text-sm mb-3 leading-relaxed">{children}</p>,
              strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
              h1: ({ children }) => <h1 className="text-lg font-bold text-white mt-4 mb-2">{children}</h1>,
              h2: ({ children }) => <h2 className="text-base font-bold text-white mt-3 mb-2">{children}</h2>,
              ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-3">{children}</ul>,
              li: ({ children }) => <li className="text-slate-300 text-sm">{children}</li>,
            }}
          >
            {insights || "Loading insights..."}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}
