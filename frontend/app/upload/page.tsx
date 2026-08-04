'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function UploadReceiptPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const clearSelection = () => {
    setFile(null);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Send the file to your FastAPI backend
      const response = await fetch('http://localhost:8000/api/receipts', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to upload receipt');
      }

      const data = await response.json();
      
      // Redirect to the review screen using the new folder structure
      if (data.receiptId) {
        router.push(`/receipts/${data.receiptId}/review`);
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-md text-black">
      <h1 className="text-2xl font-bold mb-4">Upload Grocery Receipt</h1>
      
      <div className="mb-4 border-2 border-dashed border-gray-300 p-6 text-center rounded-lg">
        {!file ? (
          <>
            <p className="text-gray-500 mb-2">Select a JPEG, PNG, or PDF</p>
            <input 
              type="file" 
              accept=".jpg,.jpeg,.png,.pdf" 
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </>
        ) : (
          <div className="flex flex-col items-center">
            <p className="text-sm font-medium text-gray-700 mb-2">Selected: {file.name}</p>
            <button 
              onClick={clearSelection}
              disabled={loading}
              className="text-red-500 text-sm hover:underline disabled:opacity-50"
            >
              Remove selection
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
          {error}
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={!file || loading}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center"
      >
        {loading ? 'Processing Receipt...' : 'Submit Receipt'}
      </button>
    </div>
  );
}