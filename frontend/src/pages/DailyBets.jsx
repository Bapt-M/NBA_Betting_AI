import React, { useState, useEffect } from 'react';
import axios from 'axios';

const DailyBets = () => {
  const [predictions, setPredictions] = useState([]);
  const [showBestBetsOnly, setShowBestBetsOnly] = useState(false);

  useEffect(() => {
    // On appelle la nouvelle route qui renvoie le JSON formaté
    axios.get('http://localhost:8000/api/predictions/json_formatted')
      .then(res => setPredictions(res.data))
      .catch(err => console.error(err));
  }, []);

  const filtered = showBestBetsOnly 
    ? predictions.filter(p => p.is_best_bet) 
    : predictions;

  return (
    <div className="flex flex-col gap-6 p-4">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-black text-slate-900 dark:text-white">Daily Predictions</h1>
        <div className="flex items-center gap-3 bg-white dark:bg-slate-900 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-800">
          <span className="text-sm font-bold text-slate-700 dark:text-slate-200">Filter:</span>
          <button 
            onClick={() => setShowBestBetsOnly(!showBestBetsOnly)}
            className={`px-3 py-1 rounded-md text-sm font-bold transition-colors ${
              showBestBetsOnly 
                ? 'bg-yellow-500 text-black shadow-lg shadow-yellow-500/20' 
                : 'bg-slate-200 dark:bg-slate-800 text-slate-500'
            }`}
          >
            ★ Best Bets Only
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800 text-sm text-left">
          <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 uppercase font-bold text-xs">
            <tr>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Match</th>
              <th className="px-4 py-3">Home</th>
              <th className="px-4 py-3">Away</th>
              <th className="px-4 py-3 text-right">Pred. Modele</th>
              <th className="px-4 py-3 text-right">Ligne Book</th>
              <th className="px-4 py-3 text-center">Type</th>
              <th className="px-4 py-3 text-right">Cote</th>
              <th className="px-4 py-3 text-right">Ecart</th>
              <th className="px-4 py-3 text-right">Confiance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-900 dark:text-white font-mono">
            {filtered.map((row, i) => (
              <tr key={i} className={`hover:bg-slate-50 dark:hover:bg-white/5 transition-colors ${row.is_best_bet ? 'bg-yellow-500/5' : ''}`}>
                <td className="px-4 py-3 text-slate-500">{row.Date}</td>
                <td className="px-4 py-3 font-bold">{row.Match}</td>
                <td className="px-4 py-3">{row.Home}</td>
                <td className="px-4 py-3">{row.Away}</td>
                <td className="px-4 py-3 text-right text-primary font-bold">{row.Prediction_Modele}</td>
                <td className="px-4 py-3 text-right">{row.Ligne_Bookmaker}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    row.Type_Pari === "OVER" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                  }`}>
                    {row.Type_Pari}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">{row.Cote}</td>
                <td className="px-4 py-3 text-right font-bold">{row.Ecart}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <span>{row.Confiance_Score}</span>
                    {row.is_best_bet && <span className="text-yellow-500 text-xs">★</span>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DailyBets;