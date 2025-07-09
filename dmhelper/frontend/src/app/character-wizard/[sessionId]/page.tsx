"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { charactersApi } from "@/lib/api";

export default function WizardSessionPage({ params }: { params: { sessionId: string } }) {
  const { sessionId } = params;
  const router = useRouter();
  const [stepInfo, setStepInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state for basic info
  const [charName, setCharName] = useState("");
  const [cls, setCls] = useState("");
  const [looks, setLooks] = useState("");
  const [doesText, setDoesText] = useState("");
  const [secret, setSecret] = useState("");

  const nextStep = async (step: string, data: any) => {
    try {
      await charactersApi.wizardStep(sessionId, step, data);
      const status = await charactersApi.getWizardStatus(sessionId);
      setStepInfo(status);
      setCharName("");
    } catch (err: any) {
      setError(err.message || "Submission failed");
    }
  };

  const finalizeNpc = async () => {
    if (!stepInfo) return;
    const templateId = stepInfo.choices?.template_id;
    const name = stepInfo.choices?.name || "Unnamed NPC";
    try {
      await charactersApi.create({
        name,
        template_id: templateId,
        race: stepInfo.choices?.race,
        class: cls,
        background: "npc",
        custom_options: { looks, does: doesText, secret }
      });
      router.push("/dm");
    } catch (err: any) {
      setError(err.message || "Failed to create NPC");
    }
  };

  const renderStep = () => {
    if (!stepInfo) return null;
    const step = stepInfo.current_step;

    switch (step) {
      case "basic_info":
        return (
          <div className="space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-gray-700">Character Name</span>
              <input
                type="text"
                value={charName}
                onChange={(e) => setCharName(e.target.value)}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </label>
            <button
              disabled={!charName.trim()}
              onClick={() => nextStep("basic-info", { name: charName.trim() })}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg disabled:bg-gray-300"
            >
              Next: Choose Race
            </button>
          </div>
        );

      case "race_selection":
        const races = [
          "Human",
          "Elf",
          "Dwarf",
          "Halfling",
          "Dragonborn",
          "Gnome",
          "Half-Elf",
          "Half-Orc",
          "Tiefling",
        ];
        return (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">Select your race:</p>
            <div className="grid gap-3 sm:grid-cols-3">
              {races.map((race) => (
                <button
                  key={race}
                  onClick={() => nextStep("race", { race })}
                  className="border border-gray-300 rounded-lg p-3 hover:bg-gray-50"
                >
                  {race}
                </button>
              ))}
            </div>
          </div>
        );

      case "class_selection":
        const classes = [
          "Fighter","Wizard","Rogue","Cleric","Ranger","Paladin","Barbarian","Bard","Druid","Monk","Sorcerer","Warlock"
        ];
        return (
          <div className="space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-gray-700">Class</span>
              <select
                value={cls}
                onChange={(e) => setCls(e.target.value)}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select class</option>
                {classes.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-gray-700">Looks</span>
              <textarea value={looks} onChange={(e)=>setLooks(e.target.value)} rows={2} className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg" />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-gray-700">Does</span>
              <textarea value={doesText} onChange={(e)=>setDoesText(e.target.value)} rows={2} className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg" />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-gray-700">Secret</span>
              <textarea value={secret} onChange={(e)=>setSecret(e.target.value)} rows={2} className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg" />
            </label>
            <button
              disabled={!cls.trim()}
              onClick={finalizeNpc}
              className="px-4 py-2 bg-green-600 text-white rounded-lg disabled:bg-gray-300"
            >
              Save NPC
            </button>
          </div>
        );

      default:
        return (
          <div>
            <p className="text-sm text-gray-500">Step UI for <strong>{step}</strong> coming soon.</p>
            <pre className="text-xs bg-gray-50 p-4 rounded-lg overflow-auto mt-4">
{JSON.stringify(stepInfo, null, 2)}
            </pre>
          </div>
        );
    }
  };

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const status = await charactersApi.getWizardStatus(sessionId);
        setStepInfo(status);
      } catch (err: any) {
        setError(err.message || "Failed to load wizard status");
      } finally {
        setLoading(false);
      }
    };
    fetchStatus();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">Loading wizard...</div>
    );
  }
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center text-red-600">{error}</div>
    );
  }
  if (!stepInfo) return null;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto bg-white shadow-sm border border-gray-200 rounded-lg p-6">
        <h1 className="text-2xl font-bold mb-4">Character Creation Wizard</h1>
        <p className="text-sm text-gray-600 mb-4">Session: {sessionId}</p>
        <h2 className="text-lg font-semibold mb-4 capitalize">Step: {stepInfo.current_step.replace('_', ' ')}</h2>
        {renderStep()}
      </div>
    </div>
  );
} 