import React, { useState, useMemo } from "react";
import { FunnelIcon, ArrowsUpDownIcon } from "@heroicons/react/24/outline";
import { CitationCard } from "./CitationCard";
import type { SearchResult, ContextSource } from "@/types/api";

interface CitationListProps {
  citations: (SearchResult | ContextSource)[];
  title?: string;
  className?: string;
  showFilters?: boolean;
  maxItems?: number;
}

type SortOption = "relevance" | "source" | "none";

export const CitationList: React.FC<CitationListProps> = ({
  citations,
  title = "Sources",
  className = "",
  showFilters = true,
  maxItems,
}) => {
  const [sortBy, setSortBy] = useState<SortOption>("relevance");
  const [minScore, setMinScore] = useState(0);
  const [sourceFilter, setSourceFilter] = useState("");

  // Get unique sources for filter dropdown
  const uniqueSources = useMemo(() => {
    const sources = citations.map((citation) => citation.source);
    return Array.from(new Set(sources)).sort();
  }, [citations]);

  // Filter and sort citations
  const filteredAndSortedCitations = useMemo(() => {
    let filtered = citations.filter((citation) => {
      const score = citation.score;
      const source = citation.source;

      return (
        score >= minScore &&
        (sourceFilter === "" ||
          source.toLowerCase().includes(sourceFilter.toLowerCase()))
      );
    });

    // Sort citations
    if (sortBy === "relevance") {
      filtered.sort((a, b) => b.score - a.score);
    } else if (sortBy === "source") {
      filtered.sort((a, b) => {
        return a.source.localeCompare(b.source);
      });
    }

    // Apply max items limit
    if (maxItems && filtered.length > maxItems) {
      filtered = filtered.slice(0, maxItems);
    }

    return filtered;
  }, [citations, sortBy, minScore, sourceFilter, maxItems]);

  if (citations.length === 0) {
    return (
      <div className={`text-center py-8 ${className}`}>
        <div className="text-gray-500">
          <p>No sources found</p>
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          {title} ({filteredAndSortedCitations.length})
        </h2>

        {showFilters && (
          <div className="flex items-center space-x-2">
            <FunnelIcon className="h-4 w-4 text-gray-400" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="text-sm border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="relevance">By Relevance</option>
              <option value="source">By Source</option>
              <option value="none">Original Order</option>
            </select>
          </div>
        )}
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Source Filter */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Filter by Source
              </label>
              <select
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value)}
                className="w-full text-sm border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">All Sources</option>
                {uniqueSources.map((source) => (
                  <option key={source} value={source}>
                    {source}
                  </option>
                ))}
              </select>
            </div>

            {/* Score Filter */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Minimum Relevance: {Math.round(minScore * 100)}%
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={minScore}
                onChange={(e) => setMinScore(parseFloat(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        </div>
      )}

      {/* Citations List */}
      {filteredAndSortedCitations.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-gray-500">
            <p>No sources match the current filters</p>
            <button
              onClick={() => {
                setMinScore(0);
                setSourceFilter("");
              }}
              className="mt-2 text-sm text-blue-600 hover:text-blue-800"
            >
              Clear filters
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredAndSortedCitations.map((citation, index) => (
            <CitationCard
              key={`citation-${index}`}
              citation={citation}
              showContent={true}
            />
          ))}

          {maxItems && citations.length > maxItems && (
            <div className="text-center py-3">
              <p className="text-sm text-gray-500">
                Showing {Math.min(maxItems, filteredAndSortedCitations.length)}{" "}
                of {citations.length} sources
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
