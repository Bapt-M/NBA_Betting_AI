import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import DailyBets from './pages/DailyBets';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="daily-bets" element={<DailyBets />} />
        {/* Placeholder pour les autres pages */}
        <Route path="*" element={<div className="p-10 text-white text-center">Page Under Construction</div>} />
      </Route>
    </Routes>
  );
}

export default App;