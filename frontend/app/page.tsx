"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [items, setItems] = useState([]);
  const [itemName, setItemName] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch the inventory list when the page loads
  useEffect(() => {
    fetch(`${API_URL}/api/inventory`)
      .then((res) => res.json())
      .then((data) => setItems(data))
      .catch(() => setError("Failed to load inventory"));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (!itemName) {
      setError("Item name is required");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/inventory`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item_name: itemName, quantity: parseInt(quantity) }),
      });

      if (!res.ok) throw new Error("Failed to save item");

      // Reset the form and fetch the updated database state
      setItemName("");
      setQuantity("1");
      const newData = await fetch(`${API_URL}/api/inventory`).then((res) => res.json());
      setItems(newData);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-md">
      <h1 className="text-2xl font-bold mb-4 text-black">PantryPilot Inventory</h1>
      
      {error && <div className="mb-4 text-red-500 text-sm">{error}</div>}

      <form onSubmit={handleSubmit} className="mb-6 flex gap-2">
        <input
          type="text"
          placeholder="Item name (e.g. Milk)"
          value={itemName}
          onChange={(e) => setItemName(e.target.value)}
          className="border p-2 flex-1 rounded text-black"
        />
        <input
          type="number"
          min="1"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          className="border p-2 w-20 rounded text-black"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {loading ? "Saving..." : "Add Item"}
        </button>
      </form>

      <ul>
        {items.map((item: any) => (
          <li key={item.id} className="border-b py-2 flex justify-between text-black">
            <span>{item.item_name}</span>
            <span className="text-gray-500">Qty: {item.quantity}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}