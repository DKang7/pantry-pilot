import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
      {/* Navbar */}
      <nav className="w-full bg-white shadow-sm py-4 px-6 md:px-12 flex justify-between items-center fixed top-0 z-50">
        <div className="flex items-center gap-2">
          <span className="text-2xl font-black text-blue-600 tracking-tighter">PantryPilot</span>
        </div>
        <div>
          <Link href="/dashboard" className="text-sm font-semibold text-gray-700 hover:text-blue-600 transition mr-6">
            Sign In
          </Link>
          <Link href="/dashboard" className="text-sm font-semibold bg-blue-600 text-white px-5 py-2.5 rounded-full hover:bg-blue-700 transition shadow-sm">
            Go to App
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="max-w-5xl mx-auto px-6 pt-40 pb-20 md:pt-48 md:pb-32 text-center">
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-gray-900 mb-6 leading-tight">
          Stop Wasting Groceries. <br className="hidden md:block" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-500">Start Cooking.</span>
        </h1>
        <p className="text-lg md:text-xl text-gray-600 mb-10 max-w-2xl mx-auto leading-relaxed">
          PantryPilot is an AI-assisted smart pantry. Snap a picture of your grocery receipt, automatically track your inventory, and get semantically retrieved, grounded recipe recommendations.
        </p>
        <div className="flex flex-col sm:flex-row justify-center items-center gap-4">
          <Link href="/dashboard" className="w-full sm:w-auto text-center font-bold bg-blue-600 text-white px-8 py-4 rounded-full hover:bg-blue-700 transition shadow-lg hover:shadow-xl transform hover:-translate-y-1">
            Enter Dashboard
          </Link>
          <a href="#how-it-works" className="w-full sm:w-auto text-center font-semibold bg-white text-gray-800 border border-gray-200 px-8 py-4 rounded-full hover:bg-gray-50 transition shadow-sm">
            See How It Works ↓
          </a>
        </div>
      </header>

      {/* How it Works Section */}
      <section id="how-it-works" className="bg-white py-24 border-t border-gray-100">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">From Receipt to Recipe</h2>
            <p className="text-gray-500 max-w-xl mx-auto">A seamless workflow powered by Deterministic Logic and AI.</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-12">
            <div className="bg-gray-50 p-8 rounded-2xl border border-gray-100 hover:shadow-md transition">
              <div className="text-4xl mb-4">📸</div>
              <h3 className="text-xl font-bold mb-2">1. Snap & Extract</h3>
              <p className="text-gray-600 text-sm leading-relaxed">Upload a grocery receipt. Our OCR and LLM pipeline extracts the raw text and standardizes items into a clean, structured draft for your review.</p>
            </div>
            <div className="bg-gray-50 p-8 rounded-2xl border border-gray-100 hover:shadow-md transition">
              <div className="text-4xl mb-4">🛡️</div>
              <h3 className="text-xl font-bold mb-2">2. Verify & Track</h3>
              <p className="text-gray-600 text-sm leading-relaxed">Human-in-the-loop review ensures accuracy. Once approved, items are added to your relational database with full transactional safety.</p>
            </div>
            <div className="bg-gray-50 p-8 rounded-2xl border border-gray-100 hover:shadow-md transition">
              <div className="text-4xl mb-4">🍳</div>
              <h3 className="text-xl font-bold mb-2">3. Cook & Deduct</h3>
              <p className="text-gray-600 text-sm leading-relaxed">Find recipes using Semantic Vector Search. Review LLM-grounded explanations, cook the meal, and let the app deduct used ingredients automatically.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Engineering Highlights */}
      <section className="py-24 bg-gray-900 text-white">
        <div className="max-w-6xl mx-auto px-6">
          <div className="mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Engineering Highlights</h2>
            <p className="text-gray-400 max-w-2xl">Built for reliability, security, and measurable evaluation.</p>
          </div>

          <div className="grid md:grid-cols-2 gap-x-12 gap-y-16">
            <div>
              <h4 className="text-blue-400 font-bold mb-2 text-lg">Hybrid Recipe Retrieval</h4>
              <p className="text-gray-300 text-sm leading-relaxed">Combines PostgreSQL deterministic filtering (for hard constraints) with pgvector semantic search to find recipes that maximize your pantry usage without violating constraints.</p>
            </div>
            <div>
              <h4 className="text-blue-400 font-bold mb-2 text-lg">Data Integrity & Security</h4>
              <p className="text-gray-300 text-sm leading-relaxed">Secured via Supabase Row Level Security (RLS). All inventory updates are executed as safe database transactions. No AI hallucination can directly modify user inventory state.</p>
            </div>
            <div>
              <h4 className="text-blue-400 font-bold mb-2 text-lg">Grounded LLM Explanations</h4>
              <p className="text-gray-300 text-sm leading-relaxed">AI explanations are strictly grounded in deterministic data. The LLM only receives the verified pantry overlap, ensuring it cannot hallucinate ingredient availability.</p>
            </div>
            <div>
              <h4 className="text-blue-400 font-bold mb-2 text-lg">Resilient Fallbacks</h4>
              <p className="text-gray-300 text-sm leading-relaxed">Designed for failure. If external LLM or vector APIs timeout or exhaust quotas, the system gracefully degrades to a fully deterministic baseline without breaking the user experience.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white py-12 border-t border-gray-200">
        <div className="max-w-6xl mx-auto px-6 text-center text-gray-500 text-sm">
          <p className="mb-4">PantryPilot &copy; {new Date().getFullYear()} — Built for Day 15</p>
          <div className="flex justify-center gap-6">
            <a href="https://github.com/pantrypilot" className="hover:text-blue-600 transition">GitHub</a>
            <a href="#" className="hover:text-blue-600 transition">Documentation</a>
            <a href="#" className="hover:text-blue-600 transition">Evaluations</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
