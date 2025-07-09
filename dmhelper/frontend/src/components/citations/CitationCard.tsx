import React, { useState } from "react";
import { formatScore, truncateContent } from "@/lib/api";
import type { SearchResult, ContextSource } from "@/types/api";

interface CitationCardProps {
  citation: SearchResult | ContextSource;
  className?: string;
  showContent?: boolean;
  maxContentLength?: number;
}

export const CitationCard: React.FC<CitationCardProps> = ({
  citation,
  className = "",
  showContent = true,
  maxContentLength = 200,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Type guard to check if it's a SearchResult
  const isSearchResult = (
    item: SearchResult | ContextSource,
  ): item is SearchResult => {
    return "content" in item;
  };

  const result = citation as SearchResult;
  const source = citation as ContextSource;

  const sourceName = isSearchResult(citation) ? result.source : source.source;
  const score = isSearchResult(citation) ? result.score : source.score;
  const content = isSearchResult(citation) ? result.content : undefined;
  const pageNumber = isSearchResult(citation) ? result.page_number : undefined;

  const handleToggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div
      className={`border border-gray-200 rounded-lg bg-white shadow-sm hover:shadow-md transition-shadow ${className}`}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center flex-1">
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium text-gray-900 truncate">
                {sourceName}
              </h3>
              <div className="flex items-center space-x-2 mt-1">
                <span className="text-xs text-gray-500">
                  Relevance: {formatScore(score)}
                </span>
                {pageNumber && (
                  <>
                    <span className="text-xs text-gray-400">•</span>
                    <span className="text-xs text-gray-500">
                      Page {pageNumber}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Score Badge */}
          <div className="flex items-center space-x-2">
            <span
              className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                score >= 0.8
                  ? "bg-green-100 text-green-800"
                  : score >= 0.6
                    ? "bg-yellow-100 text-yellow-800"
                    : "bg-gray-100 text-gray-800"
              }`}
            >
              {formatScore(score)}
            </span>

            {/* Expand Toggle */}
            {showContent && content && (
              <button
                onClick={handleToggleExpand}
                className="p-1 rounded-full hover:bg-gray-100 transition-colors text-gray-500 text-sm"
                aria-label={isExpanded ? "Collapse content" : "Expand content"}
              >
                {isExpanded ? "−" : "+"}
              </button>
            )}
          </div>
        </div>

        {/* Content Preview */}
        {showContent && content && (
          <div className="mt-3">
            <div className="text-sm text-gray-700">
              {isExpanded ? (
                <div className="whitespace-pre-wrap">{content}</div>
              ) : (
                <div className="line-clamp-3">
                  {truncateContent(content, maxContentLength)}
                </div>
              )}
            </div>

            {content.length > maxContentLength && !isExpanded && (
              <button
                onClick={handleToggleExpand}
                className="mt-1 text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                Show more
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
