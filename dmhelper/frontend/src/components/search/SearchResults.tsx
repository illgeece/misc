import React from "react";
import { CitationCard } from "@/components/citations/CitationCard";
import { formatSearchTime } from "@/lib/api";
import type { SearchResult } from "@/types/api";

interface SearchResultsProps {
  results: SearchResult[];
  query: string;
  totalResults: number;
  searchTimeMs: number;
  loading?: boolean;
  error?: string;
  className?: string;
  onResultClick?: (result: SearchResult) => void;
}

export const SearchResults: React.FC<SearchResultsProps> = ({
  results,
  query,
  totalResults,
  searchTimeMs,
  loading = false,
  error,
  className = "",
  onResultClick,
}) => {
  // Loading state
  if (loading) {
    return (
      <div className={`space-y-4 ${className}`}>
        <div className="flex items-center space-x-2 text-sm text-gray-500">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
          <span>Searching...</span>
        </div>

        {/* Loading skeletons */}
        {[...Array(3)].map((_, index) => (
          <div
            key={index}
            className="border border-gray-200 rounded-lg p-4 animate-pulse"
          >
            <div className="flex items-center space-x-2 mb-2">
              <div className="h-4 w-4 bg-gray-300 rounded"></div>
              <div className="h-4 bg-gray-300 rounded w-1/3"></div>
            </div>
            <div className="space-y-2">
              <div className="h-3 bg-gray-300 rounded w-full"></div>
              <div className="h-3 bg-gray-300 rounded w-3/4"></div>
              <div className="h-3 bg-gray-300 rounded w-1/2"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`text-center py-8 ${className}`}>
        <div className="text-red-600">
          <p className="font-medium">Search Error</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  // No results
  if (results.length === 0 && query) {
    return (
      <div className={`text-center py-8 ${className}`}>
        <h3 className="mt-2 text-sm font-medium text-gray-900">
          No results found
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          Try adjusting your search terms or check your spelling.
        </p>
        <div className="mt-4">
          <h4 className="text-xs font-medium text-gray-700 mb-2">
            Search tips:
          </h4>
          <ul className="text-xs text-gray-500 space-y-1">
            <li>• Try different keywords or phrases</li>
            <li>
              • Use broader terms (e.g., &quot;combat&quot; instead of
              &quot;opportunity attacks&quot;)
            </li>
            <li>• Check that documents are properly indexed</li>
          </ul>
        </div>
      </div>
    );
  }

  // Empty state (no query)
  if (results.length === 0 && !query) {
    return (
      <div className={`text-center py-8 ${className}`}>
        <h3 className="mt-2 text-sm font-medium text-gray-900">
          Search the knowledge base
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          Enter a query to find relevant information from your campaign
          documents.
        </p>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Search metadata */}
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-gray-200">
        <div className="flex items-center space-x-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Search Results
          </h2>
          <span className="text-sm text-gray-500">
            {totalResults} result{totalResults !== 1 ? "s" : ""} for &quot;
            {query}&quot;
          </span>
        </div>

        <div className="flex items-center space-x-1 text-xs text-gray-500">
          <span>{formatSearchTime(searchTimeMs)}</span>
        </div>
      </div>

      {/* Results list */}
      <div className="space-y-3">
        {results.map((result, index) => (
          <div
            key={`result-${index}`}
            className={onResultClick ? "cursor-pointer" : ""}
            onClick={() => onResultClick?.(result)}
          >
            <CitationCard
              citation={result}
              showContent={true}
              maxContentLength={300}
              className={
                onResultClick ? "hover:shadow-md transition-shadow" : ""
              }
            />
          </div>
        ))}
      </div>

      {/* Results summary */}
      {results.length > 0 && (
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-500">
            Showing {results.length} of {totalResults} results
          </p>
        </div>
      )}
    </div>
  );
};
