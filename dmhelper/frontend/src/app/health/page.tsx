"use client";

import React, { useEffect, useState } from "react";
import { healthApi } from "@/lib/api";

export default function HealthPage() {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await healthApi.get();
      setHealth(data);
    } catch (e: any) {
      setError(e.message || "Failed to fetch health status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <h1 className="text-2xl font-bold mb-4">System Health</h1>
        <p className="text-sm text-gray-600 mb-6">
          Live status of the backend application and key services.
        </p>

        <button
          onClick={fetchHealth}
          disabled={loading}
          className="mb-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
        >
          Refresh
        </button>

        {loading && <p className="text-gray-500 text-sm">Loading...</p>}
        {error && <p className="text-red-600 text-sm mb-2">{error}</p>}

        {health && (
          <div className="space-y-4">
            <div className="border border-gray-200 rounded-lg p-4">
              <h2 className="font-medium mb-2">Application</h2>
              <div className="grid grid-cols-2 text-sm gap-y-1">
                <span className="text-gray-600">Status:</span>
                <span className="font-medium text-gray-900">{health.status}</span>
                <span className="text-gray-600">Version:</span>
                <span className="font-medium text-gray-900">{health.version}</span>
              </div>
            </div>

            {/* Services */}
            {health.services && (
              <div className="border border-gray-200 rounded-lg p-4">
                <h2 className="font-medium mb-2">Services</h2>
                <div className="space-y-2 text-sm">
                  {Object.entries(health.services).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-gray-600 capitalize">{key}</span>
                      <span
                        className={`font-medium ${
                          value === "available" ? "text-green-700" : "text-red-700"
                        }`}
                      >
                        {String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
} 