"use client";

import React, { useEffect, useState } from "react";
import { encountersApi } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function EncounterBuilderPage() {
  const router = useRouter();
  const [partySize, setPartySize] = useState(4);
  const [partyLevel, setPartyLevel] = useState(5);
  const [difficulty, setDifficulty] = useState("medium");
  const [environment, setEnvironment] = useState<string>("");
  const [environments, setEnvironments] = useState<any[]>([]);
  const [monsters, setMonsters] = useState<any[]>([]);
  const [selectedMonster, setSelectedMonster] = useState<string>("");
  const [monsterCount, setMonsterCount] = useState<number>(1);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchEnvs = async () => {
      try {
        const envResp = await encountersApi.getEnvironments();
        setEnvironments(envResp.environments || []);
      } catch (e) {
        console.error("Failed to load environments", e);
      }
    };
    fetchEnvs();
  }, []);

  // Fetch monsters when environment changes
  useEffect(() => {
    const fetchMonsters = async () => {
      try {
        const data = await encountersApi.getMonsters(environment || undefined);
        setMonsters(data || []);
      } catch (err) {
        console.error("Failed to load monsters", err);
      }
    };
    fetchMonsters();
  }, [environment]);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const params: any = {
        party_composition: { party_size: partySize, party_level: partyLevel },
        difficulty,
        environment: environment || undefined,
      };
      if (selectedMonster) {
        params.required_monsters = [
          { monster_name: selectedMonster, count: monsterCount },
        ];
      }

      const encounter = await encountersApi.generate(params);
      setResult(encounter);
    } catch (e: any) {
      setError(e.message || "Failed to generate encounter");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <h1 className="text-2xl font-bold mb-4">Encounter Builder</h1>

        {/* Form */}
        <div className="grid gap-4 sm:grid-cols-2 mb-6">
          <label className="block">
            <span className="text-sm font-medium text-gray-700">Party Size</span>
            <input
              type="number"
              min={1}
              max={8}
              value={partySize}
              onChange={(e) => setPartySize(parseInt(e.target.value, 10))}
              className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-gray-700">Average Party Level</span>
            <input
              type="number"
              min={1}
              max={20}
              value={partyLevel}
              onChange={(e) => setPartyLevel(parseInt(e.target.value, 10))}
              className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-gray-700">Difficulty</span>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {[
                "easy",
                "medium",
                "hard",
                "deadly",
              ].map((d) => (
                <option key={d} value={d}>
                  {d.charAt(0).toUpperCase() + d.slice(1)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium text-gray-700">Environment</span>
            <select
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
              className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Any</option>
              {environments.map((env) => (
                <option key={env.value} value={env.value}>
                  {env.name}
                </option>
              ))}
            </select>
          </label>

          {/* Manual Monster Selection */}
          <div className="sm:col-span-2 grid grid-cols-2 gap-2">
            <label className="block col-span-1">
              <span className="text-sm font-medium text-gray-700">Include Monster</span>
              <select
                value={selectedMonster}
                onChange={(e) => setSelectedMonster(e.target.value)}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">None</option>
                {monsters.map((m) => (
                  <option key={m.name} value={m.name}>
                    {m.name} (CR {m.challenge_rating})
                  </option>
                ))}
              </select>
            </label>
            <label className="block col-span-1">
              <span className="text-sm font-medium text-gray-700">Count</span>
              <input
                type="number"
                min={1}
                max={12}
                value={monsterCount}
                onChange={(e) => setMonsterCount(parseInt(e.target.value, 10))}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </label>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
        >
          {loading ? "Generating..." : "Generate Encounter"}
        </button>

        {error && (
          <p className="mt-4 text-red-600 text-sm">{error}</p>
        )}

        {/* Result */}
        {result && (
          <div className="mt-8">
            <h2 className="text-xl font-semibold mb-2">Encounter Result</h2>
            <p className="text-sm text-gray-600 mb-4">
              Difficulty: {result.difficulty} – Adjusted XP: {result.adjusted_xp}
            </p>
            <div className="space-y-2">
              {result.monsters.map((m: any) => (
                <div key={m.monster.monster_name} className="border border-gray-200 rounded-lg p-4">
                  <p className="font-medium text-gray-900">
                    {m.count} × {m.monster.name} (CR {m.monster.challenge_rating})
                  </p>
                  <p className="text-xs text-gray-500">HP {m.monster.hit_points} • AC {m.monster.armor_class}</p>
                </div>
              ))}
            </div>
            <p className="mt-4 text-sm text-gray-700">
              Tactical Notes: {result.tactical_notes}
            </p>
          </div>
        )}
      </div>
    </div>
  );
} 