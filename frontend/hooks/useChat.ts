"use client";

import { useState, useEffect, useCallback } from "react";
import { Message, Chat, Source, Paper } from "@/lib/types";
import { queryRAG, queryAgent, checkHealth, indexPapers, checkIndexStatus, getPapers, uploadPaper, deletePaper } from "@/lib/api";
import { IndexStatus } from "@/lib/types";

const STORAGE_KEY = "glm-rag-chats";

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function loadChats(): Chat[] {
  if (typeof window === "undefined") return [];
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function saveChats(chats: Chat[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatHistory, setChatHistory] = useState<Chat[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [currentSources, setCurrentSources] = useState<Source[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [agentMode, setAgentMode] = useState("qa");
  const [isIndexed, setIsIndexed] = useState<boolean | null>(null); // null = checking
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexingResult, setIndexingResult] = useState<string | null>(null);
  const [collectionCount, setCollectionCount] = useState(0);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [indexProgress, setIndexProgress] = useState<IndexStatus | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [ollamaConnected, setOllamaConnected] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);

  // Check health / index status on mount
  useEffect(() => {
    let cancelled = false;
    async function check() {
      try {
        const health = await checkHealth();
        if (cancelled) return;
        setBackendOnline(true);
        setCollectionCount(health.collection_count);
        setIsIndexed(health.collection_count > 0);
        setOllamaConnected(health.ollama_connected ?? false);
        // Also fetch papers
        try {
          const papersData = await getPapers();
          if (!cancelled) setPapers(papersData.papers);
        } catch {}
      } catch {
        if (cancelled) return;
        setBackendOnline(false);
        setIsIndexed(false);
      }
    }
    check();
    return () => { cancelled = true; };
  }, []);

  const triggerIndexing = useCallback(async () => {
    setIsIndexing(true);
    setIndexingResult(null);
    setIndexProgress(null);

    try {
      await indexPapers(); // kicks off background indexing

      // Poll for progress
      const poll = setInterval(async () => {
        try {
          const status = await checkIndexStatus();
          setIndexProgress(status);

          if (status.state === "done") {
            clearInterval(poll);
            setIsIndexed(true);
            setCollectionCount(status.total_chunks);
            setIndexingResult(
              `Indexed ${status.papers_done} papers (${status.total_chunks} chunks)`
            );
            setIsIndexing(false);
          } else if (status.state === "error") {
            clearInterval(poll);
            setIndexingResult(`Indexing failed: ${status.error || "Unknown error"}`);
            setIsIndexing(false);
          }
        } catch {
          // polling failure — keep trying
        }
      }, 2000);
    } catch (error) {
      setIndexingResult(
        `Indexing failed: ${error instanceof Error ? error.message : "Unknown error"}`
      );
      setIsIndexing(false);
    }
  }, []);

  // Load chat history from localStorage on mount
  useEffect(() => {
    setChatHistory(loadChats());
  }, []);

  // Save chat history whenever it changes
  useEffect(() => {
    if (chatHistory.length > 0) {
      saveChats(chatHistory);
    }
  }, [chatHistory]);

  const saveCurrentChat = useCallback(
    (msgs: Message[]) => {
      if (msgs.length === 0) return;

      const title =
        msgs[0].content.slice(0, 50) + (msgs[0].content.length > 50 ? "..." : "");
      const now = Date.now();

      setChatHistory((prev) => {
        const existing = currentChatId
          ? prev.findIndex((c) => c.id === currentChatId)
          : -1;

        if (existing >= 0) {
          const updated = [...prev];
          updated[existing] = {
            ...updated[existing],
            messages: msgs,
            updatedAt: now,
          };
          return updated;
        }

        const newChat: Chat = {
          id: currentChatId || generateId(),
          title,
          messages: msgs,
          createdAt: now,
          updatedAt: now,
        };

        if (!currentChatId) {
          setCurrentChatId(newChat.id);
        }

        return [newChat, ...prev];
      });
    },
    [currentChatId]
  );

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim() || isLoading) return;

      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: question.trim(),
        timestamp: Date.now(),
        agentMode,
      };

      const newMessages = [...messages, userMessage];
      setMessages(newMessages);
      setIsLoading(true);
      setCurrentSources([]);

      try {
        let responseContent: string;
        let responseSources: Source[];

        if (agentMode === "qa") {
          const response = await queryRAG(question.trim());
          responseContent = response.answer;
          responseSources = response.sources;
        } else {
          const response = await queryAgent(question.trim(), agentMode);
          responseContent = response.analysis;
          responseSources = response.sources;
        }

        const assistantMessage: Message = {
          id: generateId(),
          role: "assistant",
          content: responseContent,
          sources: responseSources,
          timestamp: Date.now(),
          agentMode,
        };

        const updatedMessages = [...newMessages, assistantMessage];
        setMessages(updatedMessages);
        setCurrentSources(responseSources);
        saveCurrentChat(updatedMessages);
      } catch (error) {
        const errorMessage: Message = {
          id: generateId(),
          role: "assistant",
          content: `Error: ${error instanceof Error ? error.message : "Failed to get response"}`,
          timestamp: Date.now(),
        };

        const updatedMessages = [...newMessages, errorMessage];
        setMessages(updatedMessages);
        saveCurrentChat(updatedMessages);
      } finally {
        setIsLoading(false);
      }
    },
    [messages, isLoading, agentMode, saveCurrentChat]
  );

  const newChat = useCallback(() => {
    if (messages.length > 0) {
      saveCurrentChat(messages);
    }
    setMessages([]);
    setCurrentChatId(null);
    setCurrentSources([]);
  }, [messages, saveCurrentChat]);

  const loadChat = useCallback((id: string) => {
    const chats = loadChats();
    const chat = chats.find((c) => c.id === id);
    if (chat) {
      setMessages(chat.messages);
      setCurrentChatId(chat.id);
      const lastAssistant = [...chat.messages]
        .reverse()
        .find((m) => m.role === "assistant");
      setCurrentSources(lastAssistant?.sources || []);
    }
  }, []);

  const deleteChat = useCallback(
    (id: string) => {
      setChatHistory((prev) => {
        const filtered = prev.filter((c) => c.id !== id);
        saveChats(filtered);
        return filtered;
      });
      if (currentChatId === id) {
        setMessages([]);
        setCurrentChatId(null);
        setCurrentSources([]);
      }
    },
    [currentChatId]
  );

  const handleUpload = useCallback(async (file: File) => {
    setIsUploading(true);
    setUploadResult(null);
    try {
      const result = await uploadPaper(file);
      setUploadResult(`Indexed "${result.title}" (${result.chunk_count} chunks)`);
      // Refresh papers list
      const papersData = await getPapers();
      setPapers(papersData.papers);
      setIsIndexed(true);
      setCollectionCount(prev => prev + result.chunk_count);
    } catch (error) {
      setUploadResult(`Upload failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsUploading(false);
    }
  }, []);

  const handleDeletePaper = useCallback(async (paperId: string) => {
    try {
      await deletePaper(paperId);
      const papersData = await getPapers();
      setPapers(papersData.papers);
      const health = await checkHealth();
      setCollectionCount(health.collection_count);
      setIsIndexed(health.collection_count > 0);
    } catch (error) {
      console.error("Delete failed:", error);
    }
  }, []);

  return {
    messages,
    chatHistory,
    currentChatId,
    currentSources,
    isLoading,
    agentMode,
    setAgentMode,
    sendMessage,
    newChat,
    loadChat,
    deleteChat,
    isIndexed,
    isIndexing,
    indexingResult,
    collectionCount,
    backendOnline,
    triggerIndexing,
    indexProgress,
    papers,
    ollamaConnected,
    isUploading,
    uploadResult,
    handleUpload,
    handleDeletePaper,
  };
}
