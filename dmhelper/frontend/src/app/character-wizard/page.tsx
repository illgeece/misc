"use client";

import React, { useEffect, useState } from "react";
import { charactersApi } from "@/lib/api";
import { useRouter } from "next/navigation";

interface TemplateInfo {
  id: string;
  name: string;
  description: string;
}

export default function CharacterWizardPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initWizard = async () => {
      try {
        const session = await charactersApi.startWizard();
        setSessionId(session.session_id);
        const tpls = await charactersApi.getTemplates();
        setTemplates(tpls);
      } catch (err: any) {
        setError(err.message || "Failed to start wizard");
      } finally {
        setLoading(false);
      }
    };
    initWizard();
  }, []);

  const handleTemplateSelect = async (templateId: string) => {
    if (!sessionId) return;
    try {
      await charactersApi.wizardStep(sessionId, "template", { template_id: templateId });
      router.push(`/character-wizard/${sessionId}`); // Future detailed wizard steps
    } catch (err: any) {
      setError(err.message || "Failed to select template");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">Loading character wizard...</div>
    );
  }
  if (error) {
    return <div className="min-h-screen flex items-center justify-center text-red-600">{error}</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto bg-white shadow-sm border border-gray-200 rounded-lg p-6">
        <h1 className="text-2xl font-bold mb-4">Character Creation Wizard</h1>
        <p className="mb-6 text-sm text-gray-600">Session ID: {sessionId}</p>
        <h2 className="text-lg font-semibold mb-2">Select a Template</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {templates.map((tpl) => (
            <button
              key={tpl.id}
              onClick={() => handleTemplateSelect(tpl.id)}
              className="border border-gray-300 rounded-lg p-4 text-left hover:bg-gray-50 transition-colors"
            >
              <h3 className="font-medium text-gray-900 mb-1">{tpl.name}</h3>
              <p className="text-sm text-gray-600 line-clamp-3">{tpl.description}</p>
            </button>
          ))}
        </div>
        {templates.length === 0 && (
          <p className="text-sm text-gray-500">No templates found. You can create a character from scratch in the next steps.</p>
        )}
      </div>
    </div>
  );
} 