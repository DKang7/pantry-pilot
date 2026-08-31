'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import Link from 'next/link';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || '',
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
);

type PantryItem = {
  id: string;
  name: string;
  current_quantity: number;
  unit: string;
  purchase_date: string;
  source_type: string;
};

export default function PantryDashboard() {
  const [session, setSession] = useState<any>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authLoading, setAuthLoading] = useState(true);

  const [items, setItems] = useState<PantryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingItem, setEditingItem] = useState<PantryItem | null>(null);
  
  const [newName, setNewName] = useState('');
  const [newQuantity, setNewQuantity] = useState('');
  const [newUnit, setNewUnit] = useState('each');
  const [newDate, setNewDate] = useState(new Date().toISOString().split('T')[0]);
  const [editQuantity, setEditQuantity] = useState('');
  const [editUnit, setEditUnit] = useState('');
  const [editNote, setEditNote] = useState('');
  const [toast, setToast] = useState<{ message: string, undoAction?: () => void } | null>(null);

  const showToast = (message: string, undoAction?: () => void) => {
    setToast({ message, undoAction });
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setAuthLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchInventory = async () => {
    if (!session) return;
    setLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/inventory`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` },
        cache: 'no-store'
      });
      if (response.ok) {
        const data = await response.json();
        setItems(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (session) fetchInventory();
  }, [session]);

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) alert(error.message);
    else alert('Success! You can now log in. \n\n(Note: If it still says invalid login, you need to turn off "Confirm email" in your Supabase Auth settings!)');
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) alert(error.message);
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setItems([]);
  };

  const handleManualAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      name: newName,
      quantity: parseFloat(newQuantity),
      unit: newUnit,
      category: 'pantry',
      purchase_date: newDate
    };

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/inventory/manual`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`
      },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      const resData = await response.json();
      const addedItem = resData.data;

      setShowAddModal(false);
      fetchInventory(); 
      
      const qty = parseFloat(newQuantity);
      const name = newName;
      
      showToast(`Added ${qty} ${name}`, async () => {
         const undoPayload = { action_type: 'consume', amount: qty, note: 'Undo manual add' };
         await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/inventory/${addedItem.id}/action`, {
           method: 'POST',
           headers: { 
             'Content-Type': 'application/json',
             'Authorization': `Bearer ${session.access_token}`
           },
           body: JSON.stringify(undoPayload)
         });
         fetchInventory();
         setToast(null);
      });

      setNewName('');
      setNewQuantity('');
      setNewUnit('each');
      setNewDate(new Date().toISOString().split('T')[0]);
    }
  };

  const handleConsume = async (itemId: string, currentQty: number) => {
    const amountToConsume = currentQty >= 1 ? 1 : currentQty;
    
    // Optimistic UI Update
    setItems(currentItems => currentItems.map(item => 
      item.id === itemId 
        ? { ...item, current_quantity: Math.max(0, item.current_quantity - amountToConsume) }
        : item
    ).filter(item => item.current_quantity > 0));

    const payload = { action_type: 'consume', amount: amountToConsume, note: 'Quick consume from dashboard' };

    // Fire and forget backend call
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/inventory/${itemId}/action`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`
      },
      body: JSON.stringify(payload)
    });

    // Toast and Undo
    const consumedItem = items.find(i => i.id === itemId);
    const itemName = consumedItem ? consumedItem.name : "item";
    
    showToast(`Consumed ${amountToConsume} ${itemName}`, async () => {
      // Optimistic Undo
      setItems(currentItems => {
        const exists = currentItems.find(i => i.id === itemId);
        if (exists) {
          return currentItems.map(item => item.id === itemId ? { ...item, current_quantity: currentQty } : item);
        } else if (consumedItem) {
          return [...currentItems, { ...consumedItem, current_quantity: currentQty }];
        }
        return currentItems;
      });

      const undoPayload = { action_type: 'adjust', amount: currentQty, unit: consumedItem?.unit || 'each', note: 'Undo consume' };
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/inventory/${itemId}/action`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify(undoPayload)
      });
      setToast(null);
    });
  };

  const handleAdjust = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem) return;

    const payload = {
      action_type: 'adjust',
      amount: parseFloat(editQuantity),
      unit: editUnit,
      note: editNote || 'Manual adjustment'
    };

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/inventory/${editingItem.id}/action`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`
      },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      setEditingItem(null);
      fetchInventory();
    }
  };

  const handleDelete = async () => {
    if (!editingItem) return;

    const payload = {
      action_type: 'adjust',
      amount: 0,
      unit: editingItem.unit,
      note: 'Deleted from dashboard'
    };

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/inventory/${editingItem.id}/action`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`
      },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      setEditingItem(null);
      fetchInventory();
    }
  };

  const openEditModal = (item: PantryItem) => {
    setEditingItem(item);
    setEditQuantity(item.current_quantity.toString());
    setEditUnit(item.unit);
    setEditNote('');
  };

  if (authLoading) return <div className="p-8 text-center text-gray-500">Loading authentication...</div>;

  if (!session) {
    return (
      <div className="max-w-md mx-auto mt-20 p-6 bg-white rounded-lg shadow-md text-black">
        <h1 className="text-2xl font-bold mb-6 text-center">Welcome to PantryPilot</h1>
        <form className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1 w-full border p-2 rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="mt-1 w-full border p-2 rounded" />
          </div>
          <div className="flex gap-4 pt-4">
            <button onClick={handleLogin} className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700 font-medium">Log In</button>
            <button onClick={handleSignUp} className="flex-1 bg-gray-200 text-gray-800 py-2 rounded hover:bg-gray-300 font-medium">Sign Up</button>
          </div>
        </form>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto mt-10 p-6 bg-white rounded-lg shadow-md text-black">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <div>
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold">PantryPilot Dashboard</h1>
            <button onClick={handleSignOut} className="bg-red-50 text-red-600 px-3 py-1 rounded hover:bg-red-100 text-xs font-medium border border-red-200 transition">
              Log Out
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-1">Logged in as {session.user.email}</p>
        </div>
      </div>

      {/* Navigation & Actions */}
      <div className="flex flex-wrap items-center gap-4 mb-8 border-b pb-6 border-gray-100">
        <Link href="/upload" className="bg-blue-50 text-blue-700 px-4 py-2 rounded-lg hover:bg-blue-100 text-sm font-semibold flex items-center transition shadow-sm border border-blue-100">
          📸 Scan Receipt
        </Link>
        <Link href="/find-recipes" className="bg-green-50 text-green-700 px-4 py-2 rounded-lg hover:bg-green-100 text-sm font-semibold flex items-center transition shadow-sm border border-green-100">
          🍳 Find Recipes
        </Link>
        <button onClick={() => setShowAddModal(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium flex items-center shadow transition">
          + Add Item Manually
        </button>
      </div>

      {loading ? (
        <div className="p-8 text-center text-gray-500">Loading pantry data...</div>
      ) : items.length === 0 ? (
        <div className="text-center p-10 border-2 border-dashed border-gray-300 rounded-lg text-gray-500">
          Your pantry is currently empty.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-100 border-b-2 border-gray-200">
                <th className="p-3 text-sm font-semibold text-gray-700">Item</th>
                <th className="p-3 text-sm font-semibold text-gray-700">Quantity</th>
                <th className="hidden sm:table-cell p-3 text-sm font-semibold text-gray-700">Added</th>
                <th className="p-3 text-sm font-semibold text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="p-3 font-medium text-gray-900">{item.name}</td>
                  <td className="p-3 text-gray-700">{item.current_quantity} {item.unit}</td>
                  <td className="hidden sm:table-cell p-3 text-gray-700">{item.purchase_date || '-'}</td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-3">
                      <button onClick={() => handleConsume(item.id, item.current_quantity)} className="text-blue-600 hover:underline text-sm font-medium whitespace-nowrap">Consume 1</button>
                      <button onClick={() => openEditModal(item)} className="text-gray-500 hover:underline text-sm font-medium">Edit</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white p-6 rounded-lg shadow-lg w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Add Item Manually</h2>
            <form onSubmit={handleManualAdd} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Item Name</label>
                <input required type="text" value={newName} onChange={e => setNewName(e.target.value)} className="mt-1 w-full border p-2 rounded" />
              </div>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700">Quantity</label>
                  <input required type="number" step="0.01" min="0" value={newQuantity} onChange={e => setNewQuantity(e.target.value)} className="mt-1 w-full border p-2 rounded" />
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700">Unit</label>
                  <input required type="text" value={newUnit} onChange={e => setNewUnit(e.target.value)} placeholder="e.g. oz, boxes" className="mt-1 w-full border p-2 rounded" />
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button type="button" onClick={() => setShowAddModal(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Save Item</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editingItem && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white p-6 rounded-lg shadow-lg w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Adjust {editingItem.name}</h2>
            <form onSubmit={handleAdjust} className="space-y-4">
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700">New Quantity</label>
                  <input required type="number" step="0.01" min="0" value={editQuantity} onChange={e => setEditQuantity(e.target.value)} className="mt-1 w-full border p-2 rounded" />
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700">Unit</label>
                  <input required type="text" value={editUnit} onChange={e => setEditUnit(e.target.value)} className="mt-1 w-full border p-2 rounded" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Reason for change (optional)</label>
                <input type="text" value={editNote} onChange={e => setEditNote(e.target.value)} placeholder="e.g. Dropped one, typo" className="mt-1 w-full border p-2 rounded" />
              </div>
              <div className="flex justify-between items-center mt-6">
                <button type="button" onClick={handleDelete} className="px-4 py-2 bg-red-100 text-red-600 hover:bg-red-200 rounded font-medium text-sm">Delete Item</button>
                <div className="flex gap-2">
                  <button type="button" onClick={() => setEditingItem(null)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded">Cancel</button>
                  <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Update Item</button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50 bg-gray-900 text-white px-6 py-3 rounded-lg shadow-xl flex items-center gap-4 transition-all">
          <span className="text-sm font-medium">{toast.message}</span>
          {toast.undoAction && (
            <button 
              onClick={toast.undoAction}
              className="text-blue-300 hover:text-blue-100 text-sm font-bold uppercase tracking-wide border-l border-gray-600 pl-4"
            >
              Undo
            </button>
          )}
        </div>
      )}
    </div>
  );
}