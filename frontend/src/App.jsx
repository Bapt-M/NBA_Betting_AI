import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import DailyBets from './pages/DailyBets';
import Settings from './pages/Settings';
import Simulation from './pages/Simulation';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="daily-bets" element={<DailyBets />} />
        {/* Nouvelle route ajoutée ici */}
        <Route path="settings" element={<Settings />} />
        <Route path="simulation" element={<Simulation />} />
      </Route>
    </Routes>
  );
}

export default App;