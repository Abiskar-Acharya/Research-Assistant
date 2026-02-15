"use client";

import { useChat } from "@/hooks/useChat";
import PaperLibrary from "@/components/PaperLibrary";
import ChatPanel from "@/components/ChatPanel";
import SourcesPanel from "@/components/SourcesPanel";

export default function Home() {
  const {
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
  } = useChat();

  return (
    <main className="flex h-screen overflow-hidden">
      <PaperLibrary
        papers={papers}
        chats={chatHistory}
        currentChatId={currentChatId}
        onNewChat={newChat}
        onLoadChat={loadChat}
        onDeleteChat={deleteChat}
        onDeletePaper={handleDeletePaper}
        onUpload={handleUpload}
        isUploading={isUploading}
        uploadResult={uploadResult}
      />
      <ChatPanel
        messages={messages}
        isLoading={isLoading}
        onSendMessage={sendMessage}
        agentMode={agentMode}
        onAgentModeChange={setAgentMode}
        isIndexed={isIndexed}
        isIndexing={isIndexing}
        indexingResult={indexingResult}
        collectionCount={collectionCount}
        backendOnline={backendOnline}
        onIndexPapers={triggerIndexing}
        indexProgress={indexProgress}
        ollamaConnected={ollamaConnected}
        isUploading={isUploading}
        uploadResult={uploadResult}
        paperCount={papers.length}
      />
      <SourcesPanel sources={currentSources} papers={papers} />
    </main>
  );
}
