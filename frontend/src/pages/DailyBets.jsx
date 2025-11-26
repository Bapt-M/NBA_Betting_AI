import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { getTeamName } from '../teamMapping'; 

const DailyBets = () => {
  const [predictions, setPredictions] = useState([]);
  const [showBestBetsOnly, setShowBestBetsOnly] = useState(false);
  const [minConfidence, setMinConfidence] = useState(0);

  useEffect(() => {
    axios.get('http://localhost:8000/api/predictions/json_formatted')
      .then(res => setPredictions(res.data))
      .catch(err => console.error(err));
  }, []);

  // Fonction pour changer le Best Bet manuellement
  const toggleBestBet = async (bet) => {
    try {
      // 1. Appel Backend pour persister le changement (JSON + DB)
      await axios.put('http://localhost:8000/api/predictions/toggle_best_bet', {
        match_date: bet.Date,
        home_team: bet.Home,
        away_team: bet.Away,
        bet_type: bet.Type_Pari,
        line: bet.Ligne_Bookmaker
      });

      // 2. Mise à jour locale immédiate (Optimistic UI)
      const updatedPredictions = predictions.map(p => {
        // On cherche les paris du MÊME match
        if (p.Date === bet.Date && p.Home === bet.Home && p.Away === bet.Away) {
            // Si c'est le pari cliqué -> on inverse son statut
            if (p.Type_Pari === bet.Type_Pari && p.Ligne_Bookmaker === bet.Ligne_Bookmaker) {
                return { ...p, is_best_bet: !p.is_best_bet };
            }
            // Si c'est un autre pari du même match -> on l'éteint (Règle: 1 seul Best Bet par match)
            return { ...p, is_best_bet: false };
        }
        return p;
      });
      
      setPredictions(updatedPredictions);

    } catch (error) {
      console.error("Erreur lors du changement de Best Bet", error);
      alert("Impossible de modifier le Best Bet (Erreur Backend)");
    }
  };

  const filtered = predictions
    .filter(p => {
      if (showBestBetsOnly && !p.is_best_bet) return false;
      if (p.Confiance_Score < minConfidence) return false;
      return true;
    })
    .sort((a, b) => {
      if (a.Match !== b.Match) {
        return a.Match.localeCompare(b.Match);
      }
      return b.Confiance_Score - a.Confiance_Score;
    });

  return (
    <div className="flex flex-col gap-6 p-4">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <h1 className="text-3xl font-black text-slate-900 dark:text-white">Daily Predictions</h1>
        
        <div className="flex flex-wrap items-center gap-6 bg-white dark:bg-slate-900 px-6 py-3 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm w-full md:w-auto">
            <div className="flex flex-col gap-2 w-full md:w-48">
                <div className="flex justify-between text-xs font-bold text-slate-500 uppercase">
                    <span>Min Confidence</span>
                    <span className="text-primary">{minConfidence}%</span>
                </div>
                <input 
                    type="range" min="0" max="99" value={minConfidence} 
                    onChange={(e) => setMinConfidence(Number(e.target.value))}
                    className="h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer dark:bg-slate-700 accent-primary"
                />
            </div>
            <div className="hidden md:block h-8 w-px bg-slate-200 dark:bg-slate-700"></div>
            <div className="flex items-center gap-3">
                <span className="text-sm font-bold text-slate-700 dark:text-slate-200 hidden sm:inline">Mode:</span>
                <button 
                    onClick={() => setShowBestBetsOnly(!showBestBetsOnly)}
                    className={`px-4 py-1.5 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${
                    showBestBetsOnly 
                        ? 'bg-yellow-500 text-black shadow-lg shadow-yellow-500/20' 
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700'
                    }`}
                >
                    <span>{showBestBetsOnly ? '★' : '☆'}</span>
                    Best Bets Only
                </button>
            </div>
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
              <th className="px-4 py-3 text-center">Best Bet</th> {/* Nouvelle Colonne */}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-900 dark:text-white font-mono">
            {filtered.map((row, i) => (
              <tr key={i} className={`hover:bg-slate-50 dark:hover:bg-white/5 transition-colors ${row.is_best_bet ? 'bg-yellow-500/5' : ''}`}>
                <td className="px-4 py-3 text-slate-500">{row.Date}</td>
                <td className="px-4 py-3 font-bold">{row.Match}</td>
                
                <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{getTeamName(row.Home)}</td>
                <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{getTeamName(row.Away)}</td>
                
                <td className="px-4 py-3 text-right text-primary font-bold">{row.Prediction_Modele}</td>
                <td className="px-4 py-3 text-right">{row.Ligne_Bookmaker}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    row.Type_Pari === "OVER" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 border border-green-200 dark:border-green-800" : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800"
                  }`}>
                    {row.Type_Pari}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">{row.Cote}</td>
                <td className="px-4 py-3 text-right font-bold">{row.Ecart}</td>
                
                {/* Confiance */}
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-16 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div 
                            className={`h-full ${row.Confiance_Score > 80 ? 'bg-green-500' : row.Confiance_Score > 50 ? 'bg-blue-500' : 'bg-slate-400'}`} 
                            style={{ width: `${Math.min(row.Confiance_Score, 100)}%` }}
                        ></div>
                    </div>
                    <span className="w-8 text-right">{row.Confiance_Score}</span>
                  </div>
                </td>

                {/* BOUTON BEST BET MANUEL */}
                <td className="px-4 py-3 text-center">
                    <button 
                        onClick={() => toggleBestBet(row)}
                        className={`p-2 rounded-full transition-all ${
                            row.is_best_bet 
                            ? 'text-yellow-400 hover:bg-yellow-400/10 scale-110' 
                            : 'text-slate-600 dark:text-slate-500 hover:text-yellow-400 hover:bg-white/5'
                        }`}
                        title={row.is_best_bet ? "Retirer des Best Bets" : "Définir comme Best Bet"}
                    >
                        <span className="material-symbols-outlined text-xl">
                            {row.is_best_bet ? 'star' : 'star_border'}
                        </span>
                    </button>
                </td>

              </tr>
            ))}
            {filtered.length === 0 && (
                <tr><td colSpan="11" className="p-8 text-center text-slate-500 italic">Aucun pari ne correspond à vos critères.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DailyBets;