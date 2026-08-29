"use client";

import { useState } from "react";
import Link from "next/link";
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || '',
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
);

export default function FindRecipesPage() {
  const [queryText, setQueryText] = useState("");
  const [maxMinutes, setMaxMinutes] = useState("");
  const [maxMissing, setMaxMissing] = useState("");
  const [exclude, setExclude] = useState("");
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async () => {
    setLoading(true);
    setError("");
    setResults(null);

    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    if (!token) {
      setError("You must be logged in to find recipes.");
      setLoading(false);
      return;
    }

    const requestBody = {
      queryText: queryText.trim() || null,
      maxTotalMinutes: maxMinutes ? parseInt(maxMinutes) : null,
      maxMissingIngredients: maxMissing ? parseInt(maxMissing) : null,
      excludeIngredients: exclude ? exclude.split(",").map((s) => s.trim()) : [],
      limit: 5,
    };

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL as string;
      const res = await fetch(`${apiUrl}/api/recommendations`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(requestBody),
      });

      if (!res.ok) {
        throw new Error("Failed to fetch recommendations.");
      }

      const data = await res.json();
      setResults(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-4">
        <Link href="/" className="text-blue-600 hover:underline text-sm font-semibold">
          &larr; Back to Dashboard
        </Link>
      </div>
      <h1 className="text-3xl font-bold mb-6">Find Recipes</h1>

      {/* --- Search Controls --- */}
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">What are you in the mood for?</label>
          <input
            type="text"
            className="w-full border p-2 rounded"
            placeholder="e.g., Something warm and comforting using rice..."
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">Max Time (minutes)</label>
            <input
              type="number"
              className="w-full border p-2 rounded"
              placeholder="e.g., 30"
              value={maxMinutes}
              onChange={(e) => setMaxMinutes(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Max Missing Ingredients</label>
            <input
              type="number"
              className="w-full border p-2 rounded"
              placeholder="e.g., 2"
              value={maxMissing}
              onChange={(e) => setMaxMissing(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Exclude Ingredients</label>
            <input
              type="text"
              className="w-full border p-2 rounded"
              placeholder="e.g., peanut, dairy"
              value={exclude}
              onChange={(e) => setExclude(e.target.value)}
            />
          </div>
        </div>

        <button
          onClick={handleSearch}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Searching..." : "Find Recipes"}
        </button>
      </div>

      {error && <div className="text-red-600 mb-4">{error}</div>}

      {/* --- Results Display --- */}
      {results && (
        <div>
          <div className="mb-4 text-sm text-gray-600">
            <p>Mode: <span className="font-semibold capitalize">{results.retrievalMode}</span></p>
            <p>Algorithm: {results.algorithmVersion}</p>
          </div>

          {results.results.length === 0 ? (
            <p className="text-gray-600">No matching recipes found for your criteria.</p>
          ) : (
            <div className="space-y-6">
              {results.results.map((recipe: any) => (
                <div key={recipe.recipeId} className="border p-6 rounded-lg bg-gray-50 shadow-sm">
                  <div className="flex justify-between items-start mb-2">
                    <h2 className="text-xl font-bold">{recipe.title}</h2>
                    <div className="text-right">
                      <div className="text-2xl font-black text-blue-600">
                        {recipe.hybridScore ?? recipe.deterministicScore} pts
                      </div>
                      <div className="text-sm text-gray-500">{recipe.totalMinutes} mins</div>
                    </div>
                  </div>
                  
                  {/* Grounded Explanation Display */}
                  <div className="bg-blue-50 border-l-4 border-blue-400 p-3 mb-4 text-sm">
                    <p className="font-semibold mb-1">Why PantryPilot recommended it:</p>
                    <p>{recipe.aiExplanation || recipe.deterministicExplanation}</p>
                    {recipe.aiExplanation && (
                      <p className="text-xs text-gray-400 mt-2 italic">
                        * AI-generated explanation based on your pantry and the selected recipe.
                      </p>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                    <div>
                      <p className="font-semibold text-green-700">Available ({recipe.coveragePercent}%):</p>
                      <ul className="list-disc pl-5">
                        {recipe.matchedRequiredIngredients.map((ing: string) => (
                          <li key={ing}>{ing}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      {recipe.missingRequiredIngredients.length > 0 && (
                        <>
                          <p className="font-semibold text-red-700">Missing:</p>
                          <ul className="list-disc pl-5">
                            {recipe.missingRequiredIngredients.map((ing: string) => (
                              <li key={ing}>{ing}</li>
                            ))}
                          </ul>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Score Breakdown (Collapsible simulation via details tag) */}
                  <details className="text-xs text-gray-500 bg-white p-2 rounded border">
                    <summary className="cursor-pointer font-semibold">How this was selected</summary>
                    <div className="mt-2 space-y-1">
                      <p>Deterministic pantry score: {recipe.deterministicScore}</p>
                      {recipe.semanticScore !== null && (
                        <>
                          <p>Semantic relevance score: {recipe.semanticScore}</p>
                          <p>Hybrid math: ({recipe.deterministicScore} × 0.70) + ({recipe.semanticScore} × 0.30) = {recipe.hybridScore}</p>
                        </>
                      )}
                      <p>Source: {recipe.sourceName}</p>
                    </div>
                  </details>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}