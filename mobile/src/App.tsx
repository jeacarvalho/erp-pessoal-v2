import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [darkMode, setDarkMode] = useState(true);

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-900'}`}>
      <div className="container mx-auto px-4 py-8">
        <header className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">ERP Pessoal</h1>
          <button 
            onClick={() => setDarkMode(!darkMode)}
            className={`p-2 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-300'}`}
          >
            {darkMode ? '☀️' : '🌙'}
          </button>
        </header>
        
        <main>
          <div className="max-w-md mx-auto bg-gray-800 rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Scanner NFC-e</h2>
            <div id="qr-reader" className="w-full"></div>
            <div id="qr-reader-results" className="mt-4"></div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
