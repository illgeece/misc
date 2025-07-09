"use client";

import React, { useState } from "react";
import { SearchInput } from "@/components/search/SearchInput";
import { SearchResults } from "@/components/search/SearchResults";
import { CitationList } from "@/components/citations/CitationList";
import {
  useKnowledgeSearch,
  useDocumentSources,
  useKnowledgeStats,
} from "@/hooks/useKnowledge";
import { diceApi, charactersApi, encountersApi } from "@/lib/api";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";


type ActiveTab = "chat" | "search" | "sources";

const DiceWidget = dynamic(() => import("@/components/dice/DiceWidget"), {
  ssr: false,
});

export default function DMHelperPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");
  const [searchQuery, setSearchQuery] = useState("");
  const [chatMessage, setChatMessage] = useState("");
  const [chatHistory, setChatHistory] = useState<
    Array<{
      id: string;
      type: "user" | "assistant";
      content: string;
      timestamp: Date;
      sources?: any[];
    }>
  >([]);

  const router = useRouter();

  // Knowledge hooks
  const { searchData, isSearching, search, clearSearch } = useKnowledgeSearch();
  const { sources, isLoading: sourcesLoading } = useDocumentSources();
  const { stats } = useKnowledgeStats();

  const handleSearch = async (query: string) => {
    if (query.trim()) {
      await search({
        query: query.trim(),
        limit: 10,
        min_score: 0.1,
      });
    }
  };

  const handleSendMessage = async () => {
    if (!chatMessage.trim()) return;

    const userMessage = {
      id: Date.now().toString(),
      type: "user" as const,
      content: chatMessage,
      timestamp: new Date(),
    };

    setChatHistory((prev) => [...prev, userMessage]);
    setChatMessage("");

    // Simulate AI response with search integration
    const assistantMessage = {
      id: (Date.now() + 1).toString(),
      type: "assistant" as const,
      content: `I understand you're asking about: "${chatMessage}". Let me search the knowledge base for relevant information...`,
      timestamp: new Date(),
      sources: [],
    };

    setChatHistory((prev) => [...prev, assistantMessage]);

    // Perform search for context
    try {
      const searchResults = await search({
        query: chatMessage,
        limit: 3,
        min_score: 0.1,
      });

      // Update the assistant message with actual response and sources
      const updatedAssistant = {
        ...assistantMessage,
        content: `Based on your question about "${chatMessage}", I found some relevant information. ${
          searchResults?.results?.length > 0
            ? `Here's what I found in the knowledge base...`
            : "However, I couldn't find specific information in the indexed documents."
        }`,
        sources: searchResults?.results || [],
      };

      setChatHistory((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessage.id ? updatedAssistant : msg,
        ),
      );
    } catch (error) {
      console.error("Search failed:", error);
    }
  };

  // Quick action handlers using actual APIs
  const handleQuickAction = async (action: string) => {
    switch (action) {
      case "create-character":
        try {
          // Start character creation wizard
          const wizardSession = await charactersApi.startWizard();
          const templates = await charactersApi.getTemplates();
          
          setActiveTab("chat");
          const userMessage = {
            id: Date.now().toString(),
            type: "user" as const,
            content: "Start character creation wizard",
            timestamp: new Date(),
          };
          setChatHistory((prev) => [...prev, userMessage]);
          
          const assistantMessage = {
            id: (Date.now() + 1).toString(),
            type: "assistant" as const,
            content: `🧙‍♂️ **Character Creation Wizard Started**\n\n**Session ID:** ${wizardSession.session_id}\n\n**Available Templates:**\n${templates.map((t: any) => `• ${t.name} - ${t.description}`).join('\n')}\n\nYou can create a character from scratch or use one of these templates. The wizard will guide you through:\n1. Basic Information\n2. Race Selection\n3. Class Selection\n4. Background\n5. Ability Scores\n6. Skills & Equipment\n\nWould you like to start with a template or create from scratch?`,
            timestamp: new Date(),
            sources: [],
          };
          setChatHistory((prev) => [...prev, assistantMessage]);
        } catch (error) {
          console.error("Failed to start character creation:", error);
        }
        break;

      case "generate-encounter":
        try {
          // Generate a sample encounter (default party: 4 level 5 characters, medium difficulty)
          const encounter = await encountersApi.generate({
            party_composition: { party_size: 4, party_level: 5 },
            difficulty: "medium",
            environment: "forest"
          });
          
          setActiveTab("chat");
          const userMessage = {
            id: Date.now().toString(),
            type: "user" as const,
            content: "Generate encounter",
            timestamp: new Date(),
          };
          setChatHistory((prev) => [...prev, userMessage]);
          
          const assistantMessage = {
            id: (Date.now() + 1).toString(),
            type: "assistant" as const,
            content: `⚔️ **Generated Encounter**\n\n**Difficulty:** ${encounter.difficulty} (${encounter.adjusted_xp} XP)\n**Environment:** ${encounter.environment}\n\n**Monsters:**\n${encounter.monsters.map((m: any) => `• ${m.count}x ${m.monster_name} (CR ${m.cr})`).join('\n')}\n\n**Tactics:** ${encounter.tactical_notes}\n\n**Environmental Features:**\n${encounter.environmental_features.join('\n• ')}\n\n*Encounter balanced for 4 level 5 characters*`,
            timestamp: new Date(),
            sources: [],
          };
          setChatHistory((prev) => [...prev, assistantMessage]);
        } catch (error) {
          console.error("Failed to generate encounter:", error);
        }
        break;

      case "roll-dice":
        try {
          // Roll a d20 as example
          const diceResult = await diceApi.roll("1d20");
          
          setActiveTab("chat");
          const userMessage = {
            id: Date.now().toString(),
            type: "user" as const,
            content: "Roll dice",
            timestamp: new Date(),
          };
          setChatHistory((prev) => [...prev, userMessage]);
          
          const assistantMessage = {
            id: (Date.now() + 1).toString(),
            type: "assistant" as const,
            content: `🎲 **Dice Roll Result**\n\n**Expression:** ${diceResult.expression}\n**Result:** ${diceResult.total}\n**Breakdown:** ${diceResult.breakdown.dice_groups.map((g: any) => `${g.die_type}: ${g.rolls.map((r: any) => r.result).join(', ')}`).join('; ')}\n\nNeed to roll different dice? Just type expressions like:\n• \`1d20+5\` - Attack roll\n• \`2d6+3\` - Damage roll\n• \`4d6dl1\` - Ability score (drop lowest)\n• \`1d20adv\` - Advantage roll`,
            timestamp: new Date(),
            sources: [],
          };
          setChatHistory((prev) => [...prev, assistantMessage]);
        } catch (error) {
          console.error("Failed to roll dice:", error);
        }
        break;

      case "search-rules":
        setActiveTab("search");
        setSearchQuery("rules");
        setTimeout(() => {
          handleSearch("rules");
        }, 100);
        break;
    }
  };

  const TabButton = ({
    tab,
    label,
    count,
  }: {
    tab: ActiveTab;
    label: string;
    count?: number;
  }) => (
    <button
      onClick={() => setActiveTab(tab)}
      className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors ${
        activeTab === tab
          ? "bg-blue-100 text-blue-700"
          : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
      }`}
    >
      <span>{label}</span>
      {count !== undefined && (
        <span className="bg-gray-200 text-gray-700 px-2 py-1 rounded-full text-xs">
          {count}
        </span>
      )}
    </button>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">DM Helper</h1>
            <p className="text-sm text-gray-600">
              AI-powered Dungeon Master companion
            </p>
          </div>

          {/* Knowledge Base Stats */}
          <div className="flex items-center space-x-4 text-sm text-gray-600">
            {stats && (
              <>
                <div className="flex items-center space-x-1">
                  <span>{stats.total_documents || 0} docs</span>
                </div>
                <div className="flex items-center space-x-1">
                  <div className="h-2 w-2 rounded-full bg-green-500"></div>
                  <span>Knowledge base ready</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-2 mt-4">
          <TabButton
            tab="chat"
            label="Chat"
            count={chatHistory.length}
          />
          <TabButton
            tab="search"
            label="Search"
            count={searchData?.total_results}
          />
          <TabButton
            tab="sources"
            label="Sources"
            count={sources.length}
          />
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Primary Panel */}
          <div className="lg:col-span-2">
            {activeTab === "chat" && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="p-4 border-b border-gray-200">
                  <h2 className="text-lg font-semibold">AI Chat Assistant</h2>
                  <p className="text-sm text-gray-600">
                    Ask questions about rules, lore, and campaign information
                  </p>
                </div>

                {/* Chat Messages */}
                <div className="h-96 overflow-y-auto p-4 space-y-4">
                  {chatHistory.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                      <p className="mt-2">
                        Start a conversation with your AI assistant
                      </p>
                      <p className="text-sm">
                        Ask about rules, create characters, or get campaign
                        advice
                      </p>
                    </div>
                  ) : (
                    chatHistory.map((message) => (
                      <div
                        key={message.id}
                        className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                            message.type === "user"
                              ? "bg-blue-600 text-white"
                              : "bg-gray-100 text-gray-900"
                          }`}
                        >
                          <p className="text-sm">{message.content}</p>
                          {message.sources && message.sources.length > 0 && (
                            <div className="mt-2 text-xs opacity-80">
                              Sources: {message.sources.length} found
                            </div>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Chat Input */}
                <div className="p-4 border-t border-gray-200">
                  <div className="flex space-x-2 items-end">
                    <div className="flex-1">
                      <textarea
                        value={chatMessage}
                        onChange={(e) => setChatMessage(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                            e.preventDefault();
                            handleSendMessage();
                          }
                        }}
                        placeholder="Ask about rules, lore, characters... (Ctrl/Cmd + Enter to send)"
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                      />
                    </div>
                    <button
                      onClick={handleSendMessage}
                      disabled={!chatMessage.trim()}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed whitespace-nowrap"
                    >
                      Send
                    </button>
                  </div>
                  <div className="mt-2 text-xs text-gray-500">
                    Press Ctrl/Cmd + Enter to send your message
                  </div>
                </div>
              </div>
            )}

            {activeTab === "search" && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="mb-6">
                  <h2 className="text-lg font-semibold mb-2">
                    Knowledge Base Search
                  </h2>
                  <SearchInput
                    value={searchQuery}
                    onChange={setSearchQuery}
                    onSearch={handleSearch}
                    loading={isSearching}
                    placeholder="Search rules, lore, characters..."
                  />
                </div>

                <SearchResults
                  results={searchData?.results || []}
                  query={searchQuery}
                  totalResults={searchData?.total_results || 0}
                  searchTimeMs={searchData?.search_time_ms || 0}
                  loading={isSearching}
                />
              </div>
            )}

            {activeTab === "sources" && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="mb-6">
                  <h2 className="text-lg font-semibold">Document Sources</h2>
                  <p className="text-sm text-gray-600">
                    Manage and view indexed campaign documents
                  </p>
                </div>

                {sourcesLoading ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                    <p className="mt-2 text-gray-500">Loading sources...</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {sources.map((source, index) => (
                      <div
                        key={index}
                        className="border border-gray-200 rounded-lg p-4"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-medium text-gray-900">
                              {source.filename}
                            </h3>
                            <p className="text-sm text-gray-600">
                              {source.file_type} • {source.chunk_count} chunks
                            </p>
                          </div>
                          <div
                            className={`px-2 py-1 rounded-full text-xs ${
                              source.indexed
                                ? "bg-green-100 text-green-800"
                                : "bg-yellow-100 text-yellow-800"
                            }`}
                          >
                            {source.indexed ? "Indexed" : "Pending"}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Recent Sources */}
            {activeTab === "chat" && chatHistory.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <h3 className="font-semibold mb-3">Recent Sources</h3>
                {(() => {
                  const recentSources =
                    chatHistory
                      .filter((msg) => msg.sources && msg.sources.length > 0)
                      .slice(-1)[0]?.sources || [];

                  return recentSources.length > 0 ? (
                    <CitationList
                      citations={recentSources}
                      title=""
                      showFilters={false}
                      maxItems={3}
                    />
                  ) : (
                    <p className="text-sm text-gray-500">No sources yet</p>
                  );
                })()}
              </div>
            )}

            {/* Quick Actions */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h3 className="font-semibold mb-3">Quick Actions</h3>
              <div className="space-y-2">
                <button 
                  onClick={() => {
                    router.push("/character-wizard");
                  }}
                  className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  Create Character
                </button>
                <button 
                  onClick={() => {
                    router.push("/encounter-builder");
                  }}
                  className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  Generate Encounter
                </button>
                <button 
                  onClick={() => router.push("/admin")}
                  className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  File Watcher Controls
                </button>
                <button 
                  onClick={() => router.push("/health")}
                  className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  System Health
                </button>
                <button 
                  onClick={() => handleQuickAction("search-rules")}
                  className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  Search Rules
                </button>
                {/* Dice Roller Widget */}
                <div className="relative">
                  <DiceWidget />
                </div>
              </div>
            </div>

            {/* Knowledge Stats */}
            {stats && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <h3 className="font-semibold mb-3">Knowledge Base</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Documents:</span>
                    <span className="font-medium">{stats.total_documents || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Chunks:</span>
                    <span className="font-medium">{stats.total_chunks || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Size:</span>
                    <span className="font-medium">
                      {stats.total_size_mb?.toFixed(1) || '0.0'} MB
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
