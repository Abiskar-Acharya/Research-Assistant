import { Source, Paper } from "@/lib/types";
import SourceCard from "./SourceCard";

interface SourcesPanelProps {
  sources: Source[];
  papers: Paper[];
}

export default function SourcesPanel({ sources, papers }: SourcesPanelProps) {
  // Build filename -> title lookup map
  const titleMap: Record<string, string> = {};
  for (const paper of papers) {
    titleMap[paper.filename] = paper.title;
  }
  return (
    <div className="w-[320px] bg-[#F0EDE8] border-l border-[#E0DBD3] flex flex-col h-full shrink-0">
      <div className="p-4 border-b border-[#E0DBD3]">
        <h2 className="text-sm font-semibold text-[#1a1a1a]">Sources</h2>
        <p className="text-xs text-[#6B6560] mt-0.5">
          {sources.length > 0
            ? `${sources.length} references found`
            : "Ask a question to see sources"}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {sources.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="text-3xl mb-3 opacity-30">📄</div>
            <p className="text-xs text-[#9C9590]">
              Source documents referenced in the AI&apos;s response will appear here.
            </p>
          </div>
        ) : (
          sources.map((source, i) => (
            <SourceCard
              key={i}
              source={source}
              index={i}
              paperTitle={titleMap[source.source]}
            />
          ))
        )}
      </div>
    </div>
  );
}
