import useSWR from "swr";
import { useState, useCallback } from "react";
import { knowledgeApi, handleApiError } from "@/lib/api";
import type {
  SearchRequest,
  SearchResponse,
  DocumentSource,
  KnowledgeStats,
  SearchSuggestions,
} from "@/types/api";

// Custom hook for knowledge search
export const useKnowledgeSearch = () => {
  const [searchData, setSearchData] = useState<SearchResponse | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const search = useCallback(async (request: SearchRequest) => {
    setIsSearching(true);
    setSearchError(null);

    try {
      const result = await knowledgeApi.search(request);
      setSearchData(result);
      return result;
    } catch (error) {
      const apiError = handleApiError(error);
      setSearchError(apiError.message);
      throw apiError;
    } finally {
      setIsSearching(false);
    }
  }, []);

  const clearSearch = useCallback(() => {
    setSearchData(null);
    setSearchError(null);
  }, []);

  return {
    searchData,
    isSearching,
    searchError,
    search,
    clearSearch,
  };
};

// Hook for document sources
export const useDocumentSources = () => {
  const { data, error, isLoading, mutate } = useSWR<DocumentSource[]>(
    "/knowledge/sources",
    knowledgeApi.getSources,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      errorRetryCount: 3,
    },
  );

  return {
    sources: data || [],
    isLoading,
    error: error ? handleApiError(error).message : null,
    refresh: mutate,
  };
};

// Hook for knowledge statistics
export const useKnowledgeStats = () => {
  const { data, error, isLoading, mutate } = useSWR<KnowledgeStats>(
    "/knowledge/stats",
    knowledgeApi.getStats,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      refreshInterval: 30000, // Refresh every 30 seconds
    },
  );

  return {
    stats: data,
    isLoading,
    error: error ? handleApiError(error).message : null,
    refresh: mutate,
  };
};

// Hook for search suggestions
export const useSearchSuggestions = (query: string) => {
  const shouldFetch = query.length >= 2;

  const { data, error, isLoading } = useSWR<SearchSuggestions>(
    shouldFetch ? ["/knowledge/search/suggestions", query] : null,
    () => knowledgeApi.getSuggestions(query),
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      dedupingInterval: 1000, // Dedupe requests within 1 second
    },
  );

  return {
    suggestions: data?.suggestions || [],
    isLoading: shouldFetch ? isLoading : false,
    error: error ? handleApiError(error).message : null,
  };
};

// Hook for document indexing
export const useDocumentIndexing = () => {
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexingError, setIndexingError] = useState<string | null>(null);

  const indexDocuments = useCallback(async () => {
    setIsIndexing(true);
    setIndexingError(null);

    try {
      const result = await knowledgeApi.indexDocuments();
      return result;
    } catch (error) {
      const apiError = handleApiError(error);
      setIndexingError(apiError.message);
      throw apiError;
    } finally {
      setIsIndexing(false);
    }
  }, []);

  return {
    isIndexing,
    indexingError,
    indexDocuments,
  };
};

// Hook for knowledge service health
export const useKnowledgeHealth = () => {
  const { data, error, isLoading } = useSWR(
    "/knowledge/health",
    knowledgeApi.healthCheck,
    {
      refreshInterval: 60000, // Check every minute
      revalidateOnFocus: false,
    },
  );

  return {
    isHealthy: data?.status === "healthy",
    healthData: data,
    isLoading,
    error: error ? handleApiError(error).message : null,
  };
};
