import React from 'react';

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
            Your AI-powered Dungeon Master companion. Create characters, manage campaigns, 
            and get instant answers about rules and lore.
          </p>
          <div className="mt-10 flex items-center justify-center gap-x-6">
            <button className="btn-primary">
              Start Campaign
            </button>
            <button className="btn-secondary">
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
            <div className="mb-4">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100">
                <svg className="h-6 w-6 text-primary-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 9.75a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.184-4.183a1.14 1.14 0 01.778-.332 48.294 48.294 0 005.83-.498c1.585-.233 2.708-1.626 2.708-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                </svg>
              </div>
            </div>
            <h3 className="text-lg font-semibold text-gray-900">AI Chat Assistant</h3>
            <p className="mt-2 text-gray-600">
              Ask questions about rules, get character advice, and receive instant answers with source citations.
            </p>
          </div>

          {/* Character Creation */}
          <div className="card">
            <div className="mb-4">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100">
                <svg className="h-6 w-6 text-primary-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                </svg>
              </div>
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Character Creation</h3>
            <p className="mt-2 text-gray-600">
              Generate balanced characters from templates with automatic stat calculation and equipment.
            </p>
          </div>

          {/* Knowledge Management */}
          <div className="card">
            <div className="mb-4">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100">
                <svg className="h-6 w-6 text-primary-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0118 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
              </div>
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Campaign Knowledge</h3>
            <p className="mt-2 text-gray-600">
              Automatically index your campaign documents and search through rules, lore, and session notes.
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