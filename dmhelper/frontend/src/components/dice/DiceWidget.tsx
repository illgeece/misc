"use client";

import React, { useState } from "react";
import { diceApi } from "@/lib/api";

interface RollResult {
  expression: string;
  total: number;
  breakdown: string;
  timestamp: number;
}

export default function DiceWidget() {
  const [open, setOpen] = useState(false);
  const [expression, setExpression] = useState("1d20");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<RollResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const rollDice = async () => {
    if (!expression.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await diceApi.roll(expression.trim());
      const breakdownStr = resp.breakdown?.dice_groups
        ? resp.breakdown.dice_groups
            .map(
              (g: any) =>
                `${g.die_type}: ${g.rolls.map((r: any) => r.result).join(", ")}`,
            )
            .join("; ")
        : "";

      const newResult: RollResult = {
        expression: resp.expression || expression,
        total: resp.total,
        breakdown: breakdownStr,
        timestamp: Date.now(),
      };
      setResults((prev) => [newResult, ...prev].slice(0, 10));
    } catch (e: any) {
      setError(e.message || "Failed to roll dice");
    } finally {
      setLoading(false);
    }
  };

  const quickRoll = (expr: string) => {
    setExpression(expr);
    rollDice();
  };

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 z-50 bg-red-600 hover:bg-red-700 text-white rounded-full w-14 h-14 flex items-center justify-center shadow-lg focus:outline-none"
      >
        🎲
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-80 bg-white border border-gray-200 rounded-lg shadow-lg p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-semibold text-gray-800">Dice Roller</h3>
            <button
              onClick={() => setOpen(false)}
              className="text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          </div>

          {/* Input */}
          <div className="flex mb-3 space-x-2">
            <input
              type="text"
              value={expression}
              onChange={(e) => setExpression(e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
              placeholder="e.g. 2d6+3"
            />
            <button
              onClick={rollDice}
              disabled={loading}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-300"
            >
              Roll
            </button>
          </div>

          {/* Quick buttons */}
          <div className="grid grid-cols-6 gap-2 mb-3 text-sm">
            {[
              "d4",
              "d6",
              "d8",
              "d10",
              "d12",
              "d20",
            ].map((die) => (
              <button
                key={die}
                onClick={() => quickRoll(`1${die}`)}
                className="border border-gray-300 rounded-lg py-1 hover:bg-gray-100"
              >
                {die}
              </button>
            ))}
          </div>

          {error && <p className="text-red-600 text-sm mb-2">{error}</p>}

          {/* Results */}
          <div className="max-h-60 overflow-y-auto space-y-2 text-sm">
            {results.length === 0 ? (
              <p className="text-gray-500">No rolls yet</p>) : (
              results.map((r) => (
                <div
                  key={r.timestamp}
                  className="border border-gray-200 rounded-lg p-2"
                >
                  <div className="flex justify-between">
                    <span className="font-medium">{r.expression}</span>
                    <span className="text-red-600 font-semibold">{r.total}</span>
                  </div>
                  {r.breakdown && (
                    <p className="text-xs text-gray-500 mt-1">{r.breakdown}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </>
  );
} 