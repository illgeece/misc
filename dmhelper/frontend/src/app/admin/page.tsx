"use client";

import React, { useEffect, useState } from "react";
import { fileWatcherApi } from "@/lib/api";

export default function FileWatcherAdminPage() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const s = await fileWatcherApi.status();
      setStatus(s);
    } catch (e: any) {
      setStatus(null);
      setError(e.message || "Failed to fetch status");
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (action: "start" | "stop" | "restart") => {
    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const resp = await (action === "start"
        ? fileWatcherApi.start()
        : action === "stop"
        ? fileWatcherApi.stop()
        : fileWatcherApi.restart());
      setMessage(resp.message || `${action} successful`);
      await fetchStatus();
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || "Action failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <h1 className="text-2xl font-bold mb-4">File Watcher Admin</h1>
        <p className="text-sm text-gray-600 mb-6">
          Control and monitor the background file watcher that indexes campaign documents.
        </p>

        {/* Status */}
        <div className="mb-6">
          <h2 className="font-medium mb-2">Current Status</h2>
          {status ? (
            <pre className="bg-gray-100 text-sm rounded p-3 overflow-x-auto">
              {JSON.stringify(status, null, 2)}
            </pre>
          ) : (
            <p className="text-gray-500 text-sm">Status unavailable</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex space-x-3 mb-4">
          <button
            onClick={() => handleAction("start")}
            disabled={loading}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300"
          >
            Start
          </button>
          <button
            onClick={() => handleAction("stop")}
            disabled={loading}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-300"
          >
            Stop
          </button>
          <button
            onClick={() => handleAction("restart")}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
          >
            Restart
          </button>
          <button
            onClick={fetchStatus}
            disabled={loading}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:bg-gray-300"
          >
            Refresh
          </button>
        </div>

        {/* Feedback */}
        {message && <p className="text-green-700 text-sm mb-2">{message}</p>}
        {error && <p className="text-red-600 text-sm mb-2">{error}</p>}
      </div>
    </div>
  );
} 