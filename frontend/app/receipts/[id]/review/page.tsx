'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';

interface DraftItem {
  id: string;
  raw_text: string;
  normalized_name: string;
  quantity: number;
  unit: string;
  price: number;
  included: boolean;
}

export default function ReviewReceiptPage() {
  const params = useParams();
  const router = useRouter();
  const receiptId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [storeName, setStoreName] = useState('');
  const [purchaseDate, setPurchaseDate] = useState('');
  const [items, setItems] = useState<DraftItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReceiptData() {
      try {
        const res = await fetch(`http://localhost:8000/api/receipts/${receiptId}`);
        if (!res.ok) throw new Error('Failed to load receipt draft');
        
        const data = await res.json();
        setStoreName(data.receipt.store_name || 'Grocery Store');
        setPurchaseDate(data.receipt.purchase_date || '');
        setItems(data.items.map((i: any) => ({ ...i, included: i.included ?? true })));
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    if (receiptId) fetchReceiptData();
  }, [receiptId]);

  const handleToggleInclude = (index: number) => {
    const updated = [...items];
    updated[index].included = !updated[index].included;
    setItems(updated);
  };

  const handleFieldChange = (index: number, field: keyof DraftItem, value: any) => {
    const updated = [...items];
    updated[index] = { ...updated[index], [field]: value };
    setItems(updated);
  };

  const handleApprove = async () => {
    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch(`http://localhost:8000/api/receipts/${receiptId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to approve receipt');
      }

      // Redirect back to main dashboard upon success
      router.push('/');
    } catch (err: any) {
      setError(err.message);
      setSubmitting(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-600">Loading receipt extraction results...</div>;
  if (error && !items.length) return <div className="p-8 text-center text-red-600">Error: {error}</div>;

  const selectedCount = items.filter(i => i.included).length;

  return (
    <div className="max-w-4xl mx-auto my-10 p-6 bg-white rounded-lg shadow-md text-black">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Review Extracted Items</h1>
          <p className="text-sm text-gray-500">{storeName} {purchaseDate && `• ${purchaseDate}`}</p>
        </div>
        <span className="bg-yellow-100 text-yellow-800 text-xs px-3 py-1 rounded-full font-semibold">
          Draft State
        </span>
      </div>

      {error && <div className="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">{error}</div>}

      <div className="overflow-x-auto mb-6">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b bg-gray-50 text-xs font-semibold text-gray-600 uppercase">
              <th className="p-3">Include</th>
              <th className="p-3">Original Line Text</th>
              <th className="p-3">Pantry Item Name</th>
              <th className="p-3 w-24">Qty</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => (
              <tr key={item.id || idx} className={`border-b ${!item.included ? 'opacity-40 bg-gray-50' : ''}`}>
                <td className="p-3 text-center">
                  <input
                    type="checkbox"
                    checked={item.included}
                    onChange={() => handleToggleInclude(idx)}
                    className="w-4 h-4 cursor-pointer"
                  />
                </td>
                <td className="p-3 text-sm text-gray-500 font-mono">{item.raw_text}</td>
                <td className="p-3">
                  <input
                    type="text"
                    value={item.normalized_name || ''}
                    onChange={(e) => handleFieldChange(idx, 'normalized_name', e.target.value)}
                    disabled={!item.included}
                    className="w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-blue-500"
                  />
                </td>
                <td className="p-3">
                  <input
                    type="number"
                    value={item.quantity || 1}
                    onChange={(e) => handleFieldChange(idx, 'quantity', parseFloat(e.target.value) || 1)}
                    disabled={!item.included}
                    className="w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-blue-500"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex justify-between items-center pt-4 border-t">
        <p className="text-sm text-gray-600">
          <strong>{selectedCount}</strong> items selected for addition to pantry.
        </p>
        <button
          onClick={handleApprove}
          disabled={submitting || selectedCount === 0}
          className="bg-green-600 text-white font-semibold py-2 px-6 rounded hover:bg-green-700 disabled:opacity-50"
        >
          {submitting ? 'Adding to Pantry...' : 'Approve & Add to Pantry'}
        </button>
      </div>
    </div>
  );
}