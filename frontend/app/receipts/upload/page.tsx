'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || '',
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
);

export default function ReceiptScanner() {
  const [session, setSession] = useState<any>(null);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<'idle' | 'uploading' | 'reviewing' | 'saving'>('idle');
  const [receiptId, setReceiptId] = useState('');
  const [items, setItems] = useState<any[]>([]);
  const router = useRouter();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => setSession(session));
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !session) return;

    setStatus('uploading');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/receipts`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${session.access_token}` },
        body: formData
      });
      
      if (res.ok) {
        const data = await res.json();
        setReceiptId(data.receiptId);
        fetchReviewData(data.receiptId);
      } else {
        alert('Upload failed. Check logs.');
        setStatus('idle');
      }
    } catch (err) {
      console.error(err);
      setStatus('idle');
    }
  };

  const fetchReviewData = async (id: string) => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/receipts/${id}`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      });
      if (res.ok) {
        const data = await res.json();
        const editableItems = data.items.map((item: any) => ({
          ...item,
          included: true
        }));
        setItems(editableItems);
        setStatus('reviewing');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleApprove = async () => {
    setStatus('saving');
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/receipts/${receiptId}/approve`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({ items })
      });

      if (res.ok) {
        router.push('/');
      }
    } catch (err) {
      console.error(err);
      setStatus('reviewing');
    }
  };

  const updateItem = (index: number, field: string, value: any) => {
    const newItems = [...items];
    newItems[index][field] = value;
    setItems(newItems);
  };

  if (!session) return <div className="p-8 text-center">Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto mt-10 p-6 bg-white rounded-lg shadow-md text-black">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Scan Grocery Receipt</h1>
        <Link href="/" className="text-gray-500 hover:underline">← Back to Pantry</Link>
      </div>

      {status === 'idle' && (
        <form onSubmit={handleUpload} className="space-y-4 border-2 border-dashed border-gray-300 p-10 text-center rounded">
          <input 
            type="file" 
            accept="image/jpeg, image/png, application/pdf" 
            onChange={e => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          <div className="flex justify-center gap-4 mt-6">
            <Link href="/" className="px-6 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 font-medium border border-gray-300">
              Cancel
            </Link>
            <button type="submit" disabled={!file} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50 hover:bg-blue-700 font-medium">
              Extract Items
            </button>
          </div>
        </form>
      )}

      {status === 'uploading' && (
        <div className="text-center p-10 text-gray-600 font-medium">
          <p>Scanning receipt with AI... this may take up to 15 seconds.</p>
        </div>
      )}

      {status === 'reviewing' && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600 mb-4">Review the extracted items. Uncheck anything you don't want to add to your pantry.</p>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-100 border-b-2 border-gray-200">
                  <th className="p-3">Include</th>
                  <th className="p-3">Item Name</th>
                  <th className="p-3">Quantity</th>
                  <th className="p-3 text-gray-400">Raw Text</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, idx) => (
                  <tr key={idx} className={`border-b ${!item.included ? 'opacity-50 bg-gray-50' : ''}`}>
                    <td className="p-3">
                      <input type="checkbox" checked={item.included} onChange={e => updateItem(idx, 'included', e.target.checked)} className="h-5 w-5 rounded text-blue-600" />
                    </td>
                    <td className="p-3">
                      <input type="text" value={item.normalized_name} onChange={e => updateItem(idx, 'normalized_name', e.target.value)} className="border p-1 w-full rounded" />
                    </td>
                    <td className="p-3">
                      <input type="number" value={item.quantity} onChange={e => updateItem(idx, 'quantity', parseFloat(e.target.value))} className="border p-1 w-20 rounded" />
                    </td>
                    <td className="p-3 text-xs text-gray-400">{item.raw_text}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex justify-end gap-4 mt-6">
            <Link href="/" className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded">Cancel</Link>
            <button onClick={handleApprove} className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 font-medium">
              Approve & Add to Pantry
            </button>
          </div>
        </div>
      )}

      {status === 'saving' && (
        <div className="text-center p-10 text-gray-600 font-medium">Saving to your pantry...</div>
      )}
    </div>
  );
}