"use client";

import { useState } from "react";
import { Source } from "@/lib/types";

interface SourceCardProps {
  source: Source;
  index: number;
  paperTitle?: string;
}

export default function SourceCard({ source, index, paperTitle }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const relevance = Math.max(0, Math.round((1 - source.distance) * 100));

  const relevanceColor =
    relevance >= 70
      ? "bg-green-100 text-green-700"
      : relevance >= 40
        ? "bg-yellow-100 text-yellow-700"
        : "bg-red-100 text-red-700";

  return (
    <div
      className="bg-white border border-[#E0DBD3] rounded-lg p-3 cursor-pointer hover:border-[#B5B0A8] hover:shadow-sm transition-all"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs text-[#9C9590] font-mono shrink-0">
            #{index + 1}
          </span>
          <span className="text-xs text-[#1a1a1a] truncate font-medium">
            {paperTitle || source.source.replace(".pdf", "")}
          </span>
        </div>
        <span
          className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0 ${relevanceColor}`}
        >
          {relevance}%
        </span>
      </div>
      {source.section && (
        <span className="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 mb-1.5">
          {source.section}
        </span>
      )}
      <p
        className={`text-xs text-[#6B6560] leading-relaxed ${
          expanded ? "" : "line-clamp-3"
        }`}
      >
        {source.text}
      </p>
      {source.text.length > 150 && (
        <span className="text-[10px] text-[#B5B0A8] mt-1 block">
          {expanded ? "Click to collapse" : "Click to expand"}
        </span>
      )}
    </div>
  );
}
