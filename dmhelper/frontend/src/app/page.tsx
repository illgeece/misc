import React from "react";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Hero Section */}
      <div className="relative px-6 py-16 sm:py-24 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
            DM Helper
          </h1>
          <p className="mt-6 text-lg leading-8 text-gray-300">
            Your AI-powered Dungeon Master companion. Create characters, manage
            campaigns, and get instant answers about rules and lore.
          </p>
          <div className="mt-10 flex items-center justify-center gap-x-6">
            <a
              href="/dm"
              className="rounded-md bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              Launch DM Helper
            </a>
            <button className="rounded-md bg-white px-6 py-3 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50">
              Learn More
            </button>
          </div>
        </div>
      </div>

      {/* Features Preview */}
      <div className="mx-auto max-w-7xl px-6 py-16 lg:px-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          {/* Chat Feature */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900">
              AI Chat Assistant
            </h3>
            <p className="mt-2 text-gray-600">
              Ask questions about rules, get character advice, and receive
              instant answers with source citations.
            </p>
          </div>

          {/* Character Creation */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900">
              Character Creation
            </h3>
            <p className="mt-2 text-gray-600">
              Generate balanced characters from templates with automatic stat
              calculation and equipment.
            </p>
          </div>

          {/* Knowledge Management */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900">
              Campaign Knowledge
            </h3>
            <p className="mt-2 text-gray-600">
              Automatically index your campaign documents and search through
              rules, lore, and session notes.
            </p>
          </div>
        </div>
      </div>

      {/* Status indicator */}
      <div className="fixed bottom-4 right-4">
        <div className="rounded-lg bg-white p-2 shadow-lg">
          <div className="flex items-center space-x-2">
            <div className="h-2 w-2 rounded-full bg-green-500"></div>
            <span className="text-sm text-gray-600">Backend: Connected</span>
          </div>
        </div>
      </div>
    </div>
  );
}
