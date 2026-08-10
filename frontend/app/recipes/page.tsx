'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';

// Initialize Supabase for the frontend
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || '',
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
);

type Recipe = {
  id: string;
  title: string;
  prep_minutes: number;
  cook_minutes: number;
  cuisine: string;
  source_name: string;
  status: string;
  instructions: string[];
  description: string;
};

type RecipeIngredient = {
  id: string;
  raw_text: string;
  normalized_name: string;
  quantity: number;
  unit: string;
  preparation: string;
};

export default function RecipeInspector() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [recipeIngredients, setRecipeIngredients] = useState<RecipeIngredient[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecipes();
  }, [searchTerm]);

  const fetchRecipes = async () => {
    setLoading(true);
    try {
      let query = supabase.from('recipes').select('*').eq('status', 'active');
      
      // If there's a search term, search by title (You could expand this to search ingredients later)
      if (searchTerm) {
        query = query.ilike('title', `%${searchTerm}%`);
      }

      const { data, error } = await query.limit(50);
      if (error) throw error;
      setRecipes(data || []);
    } catch (err) {
      console.error('Error fetching recipes:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadRecipeDetails = async (recipe: Recipe) => {
    setSelectedRecipe(recipe);
    try {
      const { data, error } = await supabase
        .from('recipe_ingredients')
        .select('*')
        .eq('recipe_id', recipe.id)
        .order('sort_order');
        
      if (error) throw error;
      setRecipeIngredients(data || []);
    } catch (err) {
      console.error('Error fetching ingredients:', err);
    }
  };

  return (
    <div className="max-w-6xl mx-auto mt-10 p-6 bg-white rounded-lg shadow-md text-black flex gap-6">
      
      {/* Left Column: Search & List */}
      <div className="w-1/3 border-r pr-6">
        <h1 className="text-2xl font-bold mb-4">Recipe Inspector</h1>
        
        <input 
          type="text" 
          placeholder="Search by title..." 
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full border p-2 rounded mb-4"
        />

        {loading ? (
          <p className="text-gray-500 text-sm">Loading...</p>
        ) : (
          <div className="space-y-2 max-h-[70vh] overflow-y-auto">
            {recipes.map(recipe => (
              <div 
                key={recipe.id} 
                onClick={() => loadRecipeDetails(recipe)}
                className={`p-3 border rounded cursor-pointer hover:bg-gray-50 transition-colors ${selectedRecipe?.id === recipe.id ? 'border-blue-500 bg-blue-50' : ''}`}
              >
                <h3 className="font-semibold text-gray-900">{recipe.title}</h3>
                <p className="text-xs text-gray-500">{recipe.source_name} • {recipe.cuisine || 'Unknown cuisine'}</p>
              </div>
            ))}
            {recipes.length === 0 && <p className="text-gray-500 text-sm italic">No recipes found.</p>}
          </div>
        )}
      </div>

      {/* Right Column: Detail View */}
      <div className="w-2/3 pl-2 max-h-[85vh] overflow-y-auto">
        {selectedRecipe ? (
          <div>
            <h2 className="text-3xl font-bold text-gray-900">{selectedRecipe.title}</h2>
            <p className="text-sm text-gray-500 mb-6 italic">{selectedRecipe.description}</p>
            
            <div className="flex gap-4 mb-6 text-sm text-gray-700 bg-gray-50 p-3 rounded">
              <div><strong>Prep:</strong> {selectedRecipe.prep_minutes || '-'} mins</div>
              <div><strong>Cook:</strong> {selectedRecipe.cook_minutes || '-'} mins</div>
              <div><strong>Source:</strong> {selectedRecipe.source_name}</div>
            </div>

            <h3 className="text-xl font-semibold mb-3 border-b pb-2">Normalized Ingredients</h3>
            <table className="w-full text-left border-collapse mb-8 text-sm">
              <thead>
                <tr className="bg-gray-100 border-b">
                  <th className="p-2 text-gray-700 font-semibold">Raw Text</th>
                  <th className="p-2 text-gray-700 font-semibold">Qty</th>
                  <th className="p-2 text-gray-700 font-semibold">Unit</th>
                  <th className="p-2 text-gray-700 font-semibold">Normalized Name</th>
                  <th className="p-2 text-gray-700 font-semibold">Prep</th>
                </tr>
              </thead>
              <tbody>
                {recipeIngredients.map(ing => (
                  <tr key={ing.id} className="border-b hover:bg-gray-50">
                    <td className="p-2 text-gray-600 font-mono text-xs">{ing.raw_text}</td>
                    <td className="p-2 font-medium">{ing.quantity || '-'}</td>
                    <td className="p-2">{ing.unit || '-'}</td>
                    <td className="p-2 font-semibold text-blue-700">{ing.normalized_name || '-'}</td>
                    <td className="p-2 text-gray-500 italic">{ing.preparation || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <h3 className="text-xl font-semibold mb-3 border-b pb-2">Instructions</h3>
            <ol className="list-decimal pl-5 space-y-2 text-gray-800">
              {selectedRecipe.instructions.map((step, index) => (
                <li key={index} className="pl-2">{step}</li>
              ))}
            </ol>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-400">
            Select a recipe from the list to inspect its normalization data.
          </div>
        )}
      </div>
    </div>
  );
}