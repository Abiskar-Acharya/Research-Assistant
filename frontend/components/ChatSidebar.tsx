"use client";

import { Chat } from "@/lib/types";

interface ChatSidebarProps {
  chats: Chat[];
  currentChatId: string | null;
  onNewChat: () => void;
  onLoadChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
}

export default function ChatSidebar({
  chats,
  currentChatId,
  onNewChat,
  onLoadChat,
  onDeleteChat,
}: ChatSidebarProps) {
  return (
    <div className="w-[250px] bg-[#F0EDE8] border-r border-[#E0DBD3] flex flex-col h-full shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-[#E0DBD3]">
        <h1 className="text-sm font-bold text-[#1a1a1a] tracking-tight">
          GLM RAG
        </h1>
        <button
          onClick={onNewChat}
          className="mt-3 w-full bg-white hover:bg-[#EBE7E0] border border-[#E0DBD3] text-[#1a1a1a] text-xs rounded-lg px-3 py-2 transition-colors text-left"
        >
          + New Chat
        </button>
      </div>

      {/* Chat list */}
      <div className="flex-1 overflow-y-auto py-2">
        {chats.length === 0 ? (
          <p className="text-xs text-[#9C9590] px-4 py-2">No conversations yet</p>
        ) : (
          chats.map((chat) => (
            <div
              key={chat.id}
              className={`group flex items-center gap-2 px-4 py-2.5 cursor-pointer transition-colors ${
                currentChatId === chat.id
                  ? "bg-white border-r-2 border-[#2563eb]"
                  : "hover:bg-[#EBE7E0]"
              }`}
              onClick={() => onLoadChat(chat.id)}
            >
              <div className="flex-1 min-w-0">
                <p className="text-xs text-[#1a1a1a] truncate">{chat.title}</p>
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
                ×
              </button>
            </div>
          ))
        )}
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
