'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import Link from 'next/link';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || '',
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
);

type RecipeResult = {
  recipeId: string;
  title: string;
  totalMinutes: number;
  coveragePercent: number;
  missingRequiredIngredients: string[];
  assumedStaples: string[];
  aiExplanation: string;
};

export default function RecipeFinder() {
  const [session, setSession] = useState<any>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<RecipeResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => setSession(session));
  }, []);

  const searchRecipes = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session) return;
    
    setLoading(true);
    setHasSearched(true);
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/recommendations`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({ queryText: query, limit: 5 })
      });
      
      if (res.ok) {
        const data = await res.json();
        setResults(data.results);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!session) return <div className="p-8 text-center">Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto mt-10 p-6 bg-white rounded-lg shadow-md text-black">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Find Recipes</h1>
        <Link href="/dashboard" className="text-gray-500 hover:underline">← Back to Pantry</Link>
      </div>

      <form onSubmit={searchRecipes} className="flex gap-2 mb-8">
        <input 
          type="text" 
          value={query} 
          onChange={e => setQuery(e.target.value)} 
          placeholder="e.g., A quick dinner without dairy..." 
          className="flex-1 border p-3 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
        />
        <Link href="/dashboard" className="bg-gray-100 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-200 font-medium border border-gray-300 flex items-center justify-center">
          Cancel
        </Link>
        <button type="submit" disabled={loading} className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 font-medium disabled:opacity-50">
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      <div className="space-y-6">
        {!loading && hasSearched && results.length === 0 && (
          <p className="text-center text-gray-500 py-10">No recipes matched your pantry and request.</p>
        )}

        {results.map((recipe) => (
          <div key={recipe.recipeId} className="border p-5 rounded-lg hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-xl font-bold text-gray-900">{recipe.title}</h2>
                <p className="text-sm text-gray-500 mt-1">⏱ {recipe.totalMinutes} mins | 🛒 {Math.round(recipe.coveragePercent * 100)}% ingredients owned</p>
              </div>
            </div>
            
            <p className="mt-3 text-gray-700 text-sm bg-blue-50 p-3 rounded italic border-l-4 border-blue-500">
              {recipe.aiExplanation || "Matched based on your current pantry inventory."}
            </p>
            
            <div className="mt-4 flex gap-6 text-sm">
              {recipe.missingRequiredIngredients.length > 0 && (
                <div>
                  <span className="font-semibold text-red-600">Missing: </span>
                  <span className="text-gray-600">{recipe.missingRequiredIngredients.join(', ')}</span>
                </div>
              )}
              {recipe.assumedStaples.length > 0 && (
                <div>
                  <span className="font-semibold text-gray-500">Assumed Staples: </span>
                  <span className="text-gray-600">{recipe.assumedStaples.join(', ')}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}