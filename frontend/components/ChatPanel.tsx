"use client";

import { useState, useRef, useEffect } from "react";
import { Message, IndexStatus } from "@/lib/types";
import MessageBubble from "./MessageBubble";

interface ChatPanelProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (message: string) => void;
  agentMode: string;
  onAgentModeChange: (mode: string) => void;
  isIndexed: boolean | null;
  isIndexing: boolean;
  indexingResult: string | null;
  collectionCount: number;
  backendOnline: boolean | null;
  onIndexPapers: () => void;
  indexProgress: IndexStatus | null;
  ollamaConnected: boolean;
  isUploading: boolean;
  uploadResult: string | null;
  paperCount: number;
}

const AGENT_MODES = [
  { id: "qa", label: "Q&A", description: "Direct question answering" },
  { id: "synthesize", label: "Synthesize", description: "Cross-paper synthesis" },
  { id: "trends", label: "Trends", description: "Trend analysis" },
  { id: "gaps", label: "Gaps", description: "Research gap finding" },
];

export default function ChatPanel({
  messages,
  isLoading,
  onSendMessage,
  agentMode,
  onAgentModeChange,
  isIndexed,
  isIndexing,
  indexingResult,
  collectionCount,
  backendOnline,
  onIndexPapers,
  indexProgress,
  ollamaConnected,
  isUploading,
  uploadResult,
  paperCount,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Upload result toast auto-dismiss
  useEffect(() => {
    if (uploadResult) {
      setToastMessage(uploadResult);
      setShowToast(true);
      const timer = setTimeout(() => {
        setShowToast(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [uploadResult]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#FAF9F5] relative">
      {/* Agent mode tabs */}
      <div className="border-b border-[#E0DBD3] px-6 py-2 flex items-center gap-1">
        {AGENT_MODES.map((mode) => (
          <button
            key={mode.id}
            onClick={() => onAgentModeChange(mode.id)}
            className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
              agentMode === mode.id
                ? "bg-[#2563eb] text-white"
                : "text-[#6B6560] hover:bg-[#EBE7E0]"
            }`}
            title={mode.description}
          >
            {mode.label}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-1.5">
          <div
            className={`w-2 h-2 rounded-full ${
              backendOnline === false
                ? "bg-red-400"
                : backendOnline === true && ollamaConnected
                  ? "bg-green-400"
                  : backendOnline === true
                    ? "bg-yellow-400"
                    : "bg-gray-300"
            }`}
            title={
              backendOnline === false
                ? "Backend offline"
                : backendOnline === true && ollamaConnected
                  ? "Connected"
                  : backendOnline === true
                    ? "Ollama disconnected"
                    : "Checking..."
            }
          />
          <span className="text-[10px] text-[#9C9590]">
            {backendOnline === false
              ? "Offline"
              : backendOnline === true && ollamaConnected
                ? "Connected"
                : backendOnline === true
                  ? "No LLM"
                  : ""}
          </span>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            {/* Backend offline */}
            {backendOnline === false && (
              <>
                <div className="text-5xl mb-4">⚠️</div>
                <h2 className="text-lg font-semibold text-[#1a1a1a] mb-2">
                  Backend Unavailable
                </h2>
                <p className="text-sm text-[#6B6560] max-w-md">
                  Cannot connect to the RAG pipeline server at localhost:8000.
                  Make sure the backend is running.
                </p>
                <code className="mt-3 text-xs bg-[#EBE7E0] px-3 py-1.5 rounded-lg text-[#6B6560]">
                  make start
                </code>
              </>
            )}

            {/* Checking status */}
            {backendOnline === null && (
              <>
                <div className="text-4xl mb-4 animate-pulse">🔍</div>
                <p className="text-sm text-[#6B6560]">Connecting to backend...</p>
              </>
            )}

            {/* Backend online but not indexed */}
            {backendOnline === true && !isIndexed && (
              <>
                <div className="text-5xl mb-4">📄</div>
                <h2 className="text-lg font-semibold text-[#1a1a1a] mb-2">
                  Papers Not Indexed
                </h2>
                <p className="text-sm text-[#6B6560] max-w-md mb-4">
                  Research papers need to be indexed before you can ask questions.
                  This processes all PDFs in the papers/ directory and builds the search index.
                </p>

                {isIndexing ? (
                  <div className="flex flex-col items-center gap-3 w-full max-w-sm">
                    <div className="flex items-center gap-2">
                      <svg className="animate-spin h-5 w-5 text-[#2563eb]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      <span className="text-sm font-medium text-[#2563eb]">
                        {indexProgress && indexProgress.total_papers > 0
                          ? `Indexing paper ${indexProgress.papers_done + 1}/${indexProgress.total_papers}...`
                          : "Starting indexing..."}
                      </span>
                    </div>
                    {indexProgress && indexProgress.total_papers > 0 && (
                      <div className="w-full">
                        <div className="w-full bg-[#EBE7E0] rounded-full h-2">
                          <div
                            className="bg-[#2563eb] h-2 rounded-full transition-all duration-500"
                            style={{ width: `${Math.round((indexProgress.papers_done / indexProgress.total_papers) * 100)}%` }}
                          />
                        </div>
                        <p className="text-xs text-[#9C9590] mt-2 text-center">
                          {indexProgress.current_paper && (
                            <span className="block truncate">{indexProgress.current_paper}</span>
                          )}
                          {indexProgress.total_chunks > 0 && `${indexProgress.total_chunks} chunks so far`}
                        </p>
                      </div>
                    )}
                    {(!indexProgress || indexProgress.total_papers === 0) && (
                      <p className="text-xs text-[#9C9590]">
                        Extracting text, chunking sections, building embeddings...
                      </p>
                    )}
                  </div>
                ) : (
                  <button
                    onClick={onIndexPapers}
                    className="bg-[#2563eb] hover:bg-[#1d4ed8] text-white rounded-xl px-6 py-3 text-sm font-medium transition-colors"
                  >
                    Index Papers
                  </button>
                )}

                {indexingResult && (
                  <p className={`mt-3 text-sm ${indexingResult.startsWith("Indexing failed") ? "text-red-600" : "text-green-600"}`}>
                    {indexingResult}
                  </p>
                )}
              </>
            )}

            {/* Backend online and indexed — normal empty state */}
            {backendOnline === true && isIndexed && (
              <>
                <div className="text-5xl mb-4 opacity-30">🔬</div>
                <h2 className="text-lg font-semibold text-[#1a1a1a] mb-2">
                  ArXivMind
                </h2>
                <p className="text-sm text-[#6B6560] max-w-md">
                  {paperCount > 0
                    ? `Ask about ${paperCount} paper${paperCount === 1 ? "" : "s"}. The AI will search through your research library and provide answers with source references.`
                    : "Ask questions about indexed research papers. The AI will search through the papers and provide answers with source references."}
                </p>
                {collectionCount > 0 && (
                  <p className="mt-2 text-xs text-[#9C9590]">
                    {collectionCount} chunks indexed
                  </p>
                )}
                <div className="mt-4 flex gap-2 flex-wrap justify-center">
                  {AGENT_MODES.slice(1).map((mode) => (
                    <span
                      key={mode.id}
                      className="text-[10px] px-2 py-1 rounded-full bg-[#EBE7E0] text-[#6B6560]"
                    >
                      {mode.label}: {mode.description}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isLoading && (
              <div className="flex justify-start mb-4">
                <div className="bg-white border border-[#E0DBD3] rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 bg-[#B5B0A8] rounded-full animate-bounce [animation-delay:-0.3s]" />
                    <div className="w-2 h-2 bg-[#B5B0A8] rounded-full animate-bounce [animation-delay:-0.15s]" />
                    <div className="w-2 h-2 bg-[#B5B0A8] rounded-full animate-bounce" />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Upload result toast */}
      {showToast && toastMessage && (
        <div
          className={`absolute top-16 right-6 z-50 px-4 py-2.5 rounded-lg shadow-lg text-xs font-medium transition-all ${
            toastMessage.startsWith("Upload failed")
              ? "bg-red-50 text-red-700 border border-red-200"
              : "bg-green-50 text-green-700 border border-green-200"
          }`}
        >
          {toastMessage}
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-[#E0DBD3] p-4">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!isIndexed}
            placeholder={
              !isIndexed
                ? "Index papers first to start chatting..."
                : agentMode === "qa"
                  ? "Ask about research papers..."
                  : agentMode === "synthesize"
                    ? "What topic to synthesize across papers?"
                    : agentMode === "trends"
                      ? "What trends to analyze?"
                      : "What research gaps to find?"
            }
            rows={1}
            className="flex-1 bg-white border border-[#E0DBD3] rounded-xl px-4 py-3 text-sm text-[#1a1a1a] placeholder-[#9C9590] resize-none focus:outline-none focus:border-[#2563eb] focus:ring-1 focus:ring-[#2563eb]/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading || !isIndexed}
            className="bg-[#2563eb] hover:bg-[#1d4ed8] disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-xl px-5 py-3 text-sm font-medium transition-colors shrink-0"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
