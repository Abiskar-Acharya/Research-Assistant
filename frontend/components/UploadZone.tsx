"use client";

import { useState, useRef, useCallback } from "react";

interface UploadZoneProps {
  onUpload: (file: File) => void;
  isUploading: boolean;
  compact?: boolean;
}

export default function UploadZone({
  onUpload,
  isUploading,
  compact = false,
}: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        const file = files[0];
        if (file.type === "application/pdf") {
          onUpload(file);
        }
      }
    },
    [onUpload]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        const file = files[0];
        if (file.type === "application/pdf") {
          onUpload(file);
        }
      }
      // Reset input so the same file can be selected again
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [onUpload]
  );

  const handleClick = useCallback(() => {
    if (!isUploading) {
      fileInputRef.current?.click();
    }
  }, [isUploading]);

  if (compact) {
    return (
      <div
        className={`border border-dashed rounded-lg p-2.5 text-center cursor-pointer transition-all ${
          isDragging
            ? "border-[#2563eb] bg-blue-50/50"
            : "border-[#E0DBD3] hover:border-[#B5B0A8] hover:bg-white/50"
        } ${isUploading ? "opacity-50 cursor-not-allowed" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={handleFileSelect}
        />
        {isUploading ? (
          <div className="flex items-center justify-center gap-2">
            <svg
              className="animate-spin h-3.5 w-3.5 text-[#2563eb]"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span className="text-[10px] text-[#6B6560]">Uploading...</span>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-1.5">
            <svg
              className="w-3.5 h-3.5 text-[#9C9590]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <span className="text-[10px] text-[#6B6560]">
              {isDragging ? "Drop PDF here" : "Upload PDF"}
            </span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
        isDragging
          ? "border-[#2563eb] bg-blue-50/30"
          : "border-[#E0DBD3] hover:border-[#B5B0A8] hover:bg-[#EBE7E0]/30"
      } ${isUploading ? "opacity-50 cursor-not-allowed" : ""}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={handleFileSelect}
      />
      {isUploading ? (
        <div className="flex flex-col items-center gap-3">
          <svg
            className="animate-spin h-8 w-8 text-[#2563eb]"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <p className="text-sm text-[#6B6560]">
            Uploading and indexing paper...
          </p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <svg
            className="w-10 h-10 text-[#B5B0A8]"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <div>
            <p className="text-sm text-[#1a1a1a] font-medium">
              {isDragging ? "Drop PDF here" : "Drop PDF here or click to upload"}
            </p>
            <p className="text-xs text-[#9C9590] mt-1">PDF files only</p>
          </div>
        </div>
      )}
    </div>
  );
}
