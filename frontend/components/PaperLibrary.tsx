"use client";

import { useState } from "react";
import { Paper, Chat } from "@/lib/types";
import UploadZone from "./UploadZone";

interface PaperLibraryProps {
  papers: Paper[];
  chats: Chat[];
  currentChatId: string | null;
  onNewChat: () => void;
  onLoadChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
  onDeletePaper: (paperId: string) => void;
  onUpload: (file: File) => void;
  isUploading: boolean;
  uploadResult: string | null;
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  } catch {
    return "";
  }
}

export default function PaperLibrary({
  papers,
  chats,
  currentChatId,
  onNewChat,
  onLoadChat,
  onDeleteChat,
  onDeletePaper,
  onUpload,
  isUploading,
  uploadResult,
}: PaperLibraryProps) {
  const [historyOpen, setHistoryOpen] = useState(true);

  return (
    <div className="w-[280px] bg-[#F0EDE8] border-r border-[#E0DBD3] flex flex-col h-full shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-[#E0DBD3]">
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-[#2563eb]"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <h1 className="text-sm font-bold text-[#1a1a1a] tracking-tight">
            ArXivMind
          </h1>
        </div>
        <button
          onClick={onNewChat}
          className="mt-3 w-full bg-white hover:bg-[#EBE7E0] border border-[#E0DBD3] text-[#1a1a1a] text-xs rounded-lg px-3 py-2 transition-colors text-left"
        >
          + New Chat
        </button>
      </div>

      {/* Upload zone */}
      <div className="px-3 pt-3">
        <UploadZone onUpload={onUpload} isUploading={isUploading} compact />
        {uploadResult && (
          <p
            className={`text-[10px] mt-1.5 px-1 ${
              uploadResult.startsWith("Upload failed")
                ? "text-red-500"
                : "text-green-600"
            }`}
          >
            {uploadResult}
          </p>
        )}
      </div>

      {/* Papers list */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-4 pt-3 pb-1">
          <p className="text-[10px] font-semibold text-[#9C9590] uppercase tracking-wider">
            Papers ({papers.length})
          </p>
        </div>

        {papers.length === 0 ? (
          <div className="px-4 py-4 text-center">
            <p className="text-xs text-[#9C9590]">
              No papers indexed yet.
            </p>
            <p className="text-[10px] text-[#B5B0A8] mt-1">
              Upload a PDF or index the papers directory.
            </p>
          </div>
        ) : (
          <div className="px-2 py-1 space-y-0.5">
            {papers.map((paper) => (
              <div
                key={paper.sha256}
                className="group relative bg-white/60 hover:bg-white rounded-lg px-3 py-2 transition-colors"
              >
                <p className="text-xs text-[#1a1a1a] font-medium truncate pr-5">
                  {paper.title}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] text-[#9C9590]">
                    {paper.page_count}p
                  </span>
                  <span className="text-[10px] text-[#B5B0A8]">/</span>
                  <span className="text-[10px] text-[#9C9590]">
                    {paper.chunk_count} chunks
                  </span>
                  <span className="text-[10px] text-[#B5B0A8]">/</span>
                  <span className="text-[10px] text-[#9C9590]">
                    {formatDate(paper.indexed_at)}
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeletePaper(paper.filename);
                  }}
                  className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 text-[#9C9590] hover:text-red-500 text-xs transition-opacity"
                  title="Remove paper"
                >
                  x
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Chat history - collapsible */}
        <div className="border-t border-[#E0DBD3] mt-2">
          <button
            onClick={() => setHistoryOpen(!historyOpen)}
            className="w-full flex items-center justify-between px-4 py-2 text-[10px] font-semibold text-[#9C9590] uppercase tracking-wider hover:bg-[#EBE7E0] transition-colors"
          >
            <span>History ({chats.length})</span>
            <svg
              className={`w-3 h-3 text-[#B5B0A8] transition-transform ${
                historyOpen ? "rotate-180" : ""
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          {historyOpen && (
            <div className="pb-2">
              {chats.length === 0 ? (
                <p className="text-xs text-[#9C9590] px-4 py-2">
                  No conversations yet
                </p>
              ) : (
                chats.map((chat) => (
                  <div
                    key={chat.id}
                    className={`group flex items-center gap-2 px-4 py-2 cursor-pointer transition-colors ${
                      currentChatId === chat.id
                        ? "bg-white border-r-2 border-[#2563eb]"
                        : "hover:bg-[#EBE7E0]"
                    }`}
                    onClick={() => onLoadChat(chat.id)}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-[#1a1a1a] truncate">
                        {chat.title}
                      </p>
                      <p className="text-[10px] text-[#9C9590] mt-0.5">
                        {chat.messages.length} messages
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteChat(chat.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 text-[#9C9590] hover:text-red-500 text-xs transition-opacity"
                      title="Delete chat"
                    >
                      x
                    </button>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-[#E0DBD3]">
        <p className="text-[10px] text-[#B5B0A8] text-center">
          Powered by GLM-4 + ChromaDB
        </p>
      </div>
    </div>
  );
}
