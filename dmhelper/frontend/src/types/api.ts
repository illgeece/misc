// API Types for DM Helper
// Based on backend API models in Pydantic

export interface SearchResult {
  content: string;
  source: string;
  source_path: string;
  score: number;
  page_number?: number;
  metadata: Record<string, any>;
}

export interface SearchRequest {
  query: string;
  limit?: number;
  min_score?: number;
  source_filter?: string[];
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  search_time_ms: number;
  min_score: number;
}

export interface DocumentSource {
  filename: string;
  filepath: string;
  file_type: string;
  chunk_count: number;
  indexed: boolean;
}

export interface KnowledgeStats {
  total_documents: number;
  total_chunks: number;
  total_size_mb: number;
  supported_formats: string[];
  last_updated: string;
}

export interface SearchSuggestions {
  suggestions: string[];
}

// Chat API Types
export interface ChatRequest {
  message: string;
  session_id?: string;
  use_rag?: boolean;
  use_tools?: boolean;
  context_limit?: number;
}

export interface ContextSource {
  source: string;
  score: number;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  model: string;
  response_time_ms: number;
  context_used: boolean;
  context_sources: ContextSource[];
  conversation_length: number;
}

export interface ContextQueryRequest {
  question: string;
  context_sources?: string[];
  max_context?: number;
}

export interface ContextQueryResponse {
  question: string;
  response: string;
  context_used: boolean;
  sources: SearchResult[];
  model: string;
  response_time_ms: number;
  error?: string;
}

// UI State Types
export interface SearchFilters {
  sources?: string[];
  minScore?: number;
  fileTypes?: string[];
}

export interface ChatMessage {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: ContextSource[];
  loading?: boolean;
}

export interface SearchState {
  query: string;
  results: SearchResult[];
  loading: boolean;
  error?: string;
  filters: SearchFilters;
  totalResults: number;
  searchTimeMs: number;
}
