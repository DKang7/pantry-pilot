"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { v4 as uuidv4 } from "uuid";

export default function RecipeDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  
  const [recipe, setRecipe] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Cooking Review State
  const [isReviewing, setIsReviewing] = useState(false);
  const [cookingDraft, setCookingDraft] = useState<any>(null);
  const [idempotencyKey, setIdempotencyKey] = useState("");

  useEffect(() => {
    // Simulating fetching recipe details
    setTimeout(() => {
      setRecipe({
        id: id,
        title: "Vegetable Fried Rice",
        sourceName: "PantryPilot Originals",
        sourceUrl: "https://example.com/fried-rice",
        description: "A quick, comforting classic using everyday staples.",
        prepTime: 10,
        cookTime: 15,
        totalMinutes: 25,
        servings: 2,
        dietaryTags: ["Vegetarian", "Dairy-Free"],
        instructions: [
          "Heat oil in a large skillet or wok over medium-high heat.",
          "Add chopped vegetables and stir-fry until tender.",
          "Push vegetables to the side, scramble the eggs in the center.",
          "Stir in the cooked rice and soy sauce, mixing thoroughly."
        ],
        ingredients: [
          { name: "2 cups cooked rice", status: "Available", type: "exact_match", missing: false },
          { name: "2 eggs", status: "Available", type: "exact_match", missing: false },
          { name: "1 green onion", status: "Missing", type: "missing", missing: true },
          { name: "1 tbsp oil", status: "Assumed staple", type: "assumed_staple", missing: false }
        ],
        aiExplanation: "Vegetable Fried Rice is recommended as a comforting, quick dinner that utilizes your available rice and eggs."
      });
      setLoading(false);
    }, 500);
  }, [id]);

  const getHeaders = () => {
    const token = localStorage.getItem("supabase_token");
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    };
  };

  const handleSave = async () => {
    setIsSubmitting(true);
    setActionMessage("");
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/recipes/${id}/save`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify({ recommendationRunId: null }),
      });
      if (res.ok) setActionMessage("Recipe saved. ✔️");
      else setActionMessage("Failed to save recipe.");
    } catch (err) {
      setActionMessage("Network error occurred.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDismiss = () => {
    setActionMessage("Recommendation dismissed. (Undo)");
  };

  // --- Cooking Workflow Functions ---

  const handleCooked = async () => {
    setIsSubmitting(true);
    setActionMessage("");
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/recipes/${id}/cooking-draft`, {
        method: "POST",
        headers: getHeaders(),
      });
      
      if (!res.ok) throw new Error("Failed to generate draft");
      
      const data = await res.json();
      setCookingDraft(data.data);
      setIdempotencyKey(uuidv4()); // Generate unique key for this session
      setIsReviewing(true);
    } catch (err) {
      setActionMessage("Failed to load pantry deductions.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuantityChange = (idx: number, newQty: number) => {
    const updated = { ...cookingDraft };
    updated.items[idx].proposedQuantity = newQty;
    updated.items[idx].remainingQuantity = Math.max(0, updated.items[idx].currentQuantity - newQty);
    setCookingDraft(updated);
  };

  const handleToggleInclude = (idx: number) => {
    const updated = { ...cookingDraft };
    updated.items[idx].included = !updated.items[idx].included;
    setCookingDraft(updated);
  };

  const submitCookingSession = async (skipPantryUpdates = false) => {
    setIsSubmitting(true);
    setActionMessage("");
    
    // Filter out items that are not included or have no valid pantry match
    const deductions = skipPantryUpdates ? [] : cookingDraft.items
      .filter((item: any) => item.included && item.pantryItemId && item.proposedQuantity > 0)
      .map((item: any) => ({
        pantryItemId: item.pantryItemId,
        recipeIngredientId: item.recipeIngredientId,
        quantity: item.proposedQuantity,
        unit: item.unit
      }));

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/recipes/${id}/cooking-complete`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify({
          idempotencyKey,
          recommendationRunId: null,
          deductions
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to complete cooking session");
      }

      setActionMessage("Cooking session completed and inventory updated! 🎉");
      setIsReviewing(false);
    } catch (err: any) {
      setActionMessage(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <div className="p-6 text-center">Loading recipe details...</div>;
  if (!recipe) return <div className="p-6 text-center text-red-600">Recipe not found.</div>;

  // --- Render Deduction Review Screen ---
  if (isReviewing && cookingDraft) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-2">Review Pantry Updates</h1>
        <p className="text-gray-600 mb-6">Review the proposed deductions for <strong>{recipe.title}</strong> before confirming.</p>

        {cookingDraft.warnings?.length > 0 && (
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
            <h3 className="font-bold text-yellow-800">Warnings</h3>
            <ul className="list-disc pl-5 text-sm text-yellow-700 mt-2 space-y-1">
              {cookingDraft.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        )}

        {actionMessage && (
          <div className="mb-6 text-sm font-medium text-red-700 bg-red-50 p-3 rounded border border-red-200">
            {actionMessage}
          </div>
        )}

        <div className="overflow-x-auto bg-white rounded shadow mb-8">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-100 text-gray-700 text-sm">
                <th className="p-3 border-b">Update</th>
                <th className="p-3 border-b">Ingredient</th>
                <th className="p-3 border-b">Current</th>
                <th className="p-3 border-b">Deduct</th>
                <th className="p-3 border-b">Remaining</th>
                <th className="p-3 border-b">Status</th>
              </tr>
            </thead>
            <tbody>
              {cookingDraft.items.map((item: any, idx: number) => (
                <tr key={idx} className="border-b text-sm">
                  <td className="p-3">
                    <input 
                      type="checkbox" 
                      checked={item.included}
                      disabled={!item.pantryItemId}
                      onChange={() => handleToggleInclude(idx)}
                      className="w-4 h-4 cursor-pointer"
                    />
                  </td>
                  <td className="p-3 font-medium">{item.ingredientName}</td>
                  <td className="p-3">{item.pantryItemId ? `${item.currentQuantity} ${item.unit}` : "—"}</td>
                  <td className="p-3">
                    {item.pantryItemId ? (
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          min="0"
                          max={item.currentQuantity}
                          step="0.1"
                          value={item.proposedQuantity || 0}
                          onChange={(e) => handleQuantityChange(idx, parseFloat(e.target.value) || 0)}
                          disabled={!item.included}
                          className="border rounded p-1 w-20 text-center"
                        />
                        <span className="text-xs text-gray-500">{item.unit}</span>
                      </div>
                    ) : "—"}
                  </td>
                  <td className="p-3">{item.pantryItemId ? `${item.remainingQuantity} ${item.unit}` : "—"}</td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      item.matchingStatus === "exact_match" ? "bg-green-100 text-green-800" :
                      item.matchingStatus === "missing" ? "bg-red-100 text-red-800" : "bg-yellow-100 text-yellow-800"
                    }`}>
                      {item.matchingStatus.replace("_", " ")}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-between items-center">
          <button 
            onClick={() => setIsReviewing(false)} 
            disabled={isSubmitting}
            className="text-gray-600 hover:underline"
          >
            Cancel
          </button>
          <div className="flex gap-4">
            <button 
              onClick={() => submitCookingSession(true)}
              disabled={isSubmitting}
              className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300 disabled:opacity-50"
            >
              Mark as cooked without updating pantry
            </button>
            <button 
              onClick={() => submitCookingSession(false)}
              disabled={isSubmitting}
              className="bg-blue-600 text-white px-6 py-2 rounded font-bold hover:bg-blue-700 disabled:opacity-50"
            >
              Confirm Pantry Updates
            </button>
          </div>
        </div>
      </div>
    );
  }

  // --- Render Normal Recipe Detail Screen ---
  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="mb-6 border-b pb-4">
        <h1 className="text-4xl font-bold mb-2">{recipe.title}</h1>
        <p className="text-sm text-gray-500 mb-4">
          Source: {recipe.sourceUrl ? (
            <a href={recipe.sourceUrl} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">
              {recipe.sourceName}
            </a>
          ) : recipe.sourceName}
        </p>
        <p className="text-gray-700 italic">{recipe.description}</p>
      </div>

      {recipe.aiExplanation && (
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6 rounded">
          <p className="font-semibold text-blue-900 mb-1">Why PantryPilot recommended this:</p>
          <p className="text-blue-800 text-sm">{recipe.aiExplanation}</p>
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-8 bg-gray-50 p-4 rounded-lg shadow-sm">
        <button 
          onClick={handleSave} 
          disabled={isSubmitting}
          className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300 disabled:opacity-50 font-medium"
        >
          💾 Save Recipe
        </button>
        <button 
          onClick={handleDismiss}
          disabled={isSubmitting}
          className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300 disabled:opacity-50 font-medium"
        >
          ✕ Dismiss
        </button>
        <button 
          onClick={handleCooked}
          disabled={isSubmitting}
          className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700 disabled:opacity-50 font-bold ml-auto shadow"
        >
          🍳 I Cooked This
        </button>
      </div>

      {actionMessage && (
        <div className="mb-6 text-sm font-medium text-green-700 bg-green-50 p-3 rounded border border-green-200">
          {actionMessage}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 text-sm bg-white p-4 rounded-lg border">
        <div><span className="font-semibold block">Prep Time</span> {recipe.prepTime} mins</div>
        <div><span className="font-semibold block">Cook Time</span> {recipe.cookTime} mins</div>
        <div><span className="font-semibold block">Total Time</span> {recipe.totalMinutes} mins</div>
        <div><span className="font-semibold block">Servings</span> {recipe.servings}</div>
      </div>

      {recipe.dietaryTags?.length > 0 && (
        <div className="mb-8 flex gap-2">
          {recipe.dietaryTags.map((tag: string) => (
            <span key={tag} className="bg-gray-200 text-gray-700 px-3 py-1 rounded-full text-xs font-semibold">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-1">
          <h2 className="text-2xl font-bold mb-4 border-b pb-2">Ingredients</h2>
          <ul className="space-y-4">
            {recipe.ingredients.map((ing: any, idx: number) => (
              <li key={idx} className="flex flex-col text-sm border-b pb-2 last:border-0">
                <span className="font-medium text-gray-900">{ing.name}</span>
                <span className={`text-xs font-semibold mt-1 ${ing.missing ? 'text-red-600' : 'text-green-600'}`}>
                  {ing.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="md:col-span-2">
          <h2 className="text-2xl font-bold mb-4 border-b pb-2">Instructions</h2>
          <ol className="list-decimal pl-5 space-y-4 text-gray-800">
            {recipe.instructions.map((step: string, idx: number) => (
              <li key={idx} className="leading-relaxed pl-2">{step}</li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}