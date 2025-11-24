import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

const Analytics = () => {
  const [data, setData] = useState([]); // Toutes les données (History + Pending)
  const [filteredData, setFilteredData] = useState([]); // Données affichées
  const [simulation, setSimulation] = useState({ daily: [], totalProfit: 0, avgProfit: 0, comboList: [] });
  
  const [stake, setStake] = useState(10);
  const [activeTab, setActiveTab] = useState('history');
  const [selectedDate, setSelectedDate] = useState(''); // '' = All Time

  useEffect(() => {
    fetchAllData();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [data, selectedDate]);

  useEffect(() => {
    runSimulation();
  }, [filteredData, stake]);

  const fetchAllData = async () => {
    try {
      // 1. Historique (Résultats connus)
      const resHistory = await axios.get('http://localhost:8000/api/predictions/history');
      // 2. En attente (Prédictions du jour ou futures)
      const resPending = await axios.get('http://localhost:8000/api/predictions/today');
      
      // Fusion et tri par date (plus récent en premier)
      const combined = [...resPending.data, ...resHistory.data].sort((a, b) => 
        new Date(b.match_date) - new Date(a.match_date)
      );
      
      setData(combined);
    } catch (err) {
      console.error("Erreur chargement données", err);
    }
  };

  const applyFilters = () => {
    if (!selectedDate) {
      setFilteredData(data);
    } else {
      setFilteredData(data.filter(d => d.match_date === selectedDate));
    }
  };

  // --- MOTEUR DE SIMULATION (Combinés 2 matchs) ---
  const runSimulation = () => {
    // On ne garde que les paris "Best Bet" pour la simulation
    const relevantBets = filteredData.filter(p => 
      p.recommendation === "Best Bet" || p.recommendation === "High Confidence"
    );
    
    const betsByDate = relevantBets.reduce((acc, bet) => {
      if (!acc[bet.match_date]) acc[bet.match_date] = [];
      acc[bet.match_date].push(bet);
      return acc;
    }, {});

    const dailyResults = [];
    const allCombos = [];
    let globalProfit = 0;

    // On parcourt les dates dans l'ordre chronologique pour le graphique
    const sortedDates = Object.keys(betsByDate).sort();

    sortedDates.forEach(date => {
      const bets = betsByDate[date];
      let dayProfit = 0;

      // Générer combinés 2 par 2
      for (let i = 0; i < bets.length; i++) {
        for (let j = i + 1; j < bets.length; j++) {
          const betA = bets[i];
          const betB = bets[j];

          // Cote simulée si non présente (1.90 standard NBA)
          const oddA = 1.90;
          const oddB = 1.90;
          const comboOdd = oddA * oddB;

          let status = "PENDING";
          let profit = 0;

          // Si l'un des deux n'est pas traité (is_processed=False), le combiné est en attente
          if (!betA.is_processed || !betB.is_processed) {
            status = "PENDING";
            profit = 0; 
          } else {
            // Résolution
            if (betA.bet_result === "WIN" && betB.bet_result === "WIN") {
              status = "WIN";
              profit = (stake * comboOdd) - stake;
            } else if (betA.bet_result === "LOSS" || betB.bet_result === "LOSS") {
              status = "LOSS";
              profit = -stake;
            } else {
              status = "VOID";
            }
          }

          // On n'ajoute au profit du jour que si le résultat est connu
          if (status !== "PENDING") {
            dayProfit += profit;
          }

          allCombos.push({
            id: `${betA.id}-${betB.id}`,
            date,
            matches: [
              { ...betA, odd: oddA },
              { ...betB, odd: oddB }
            ],
            totalOdd: comboOdd.toFixed(2),
            status,
            profit: status === "PENDING" ? 0 : profit.toFixed(2)
          });
        }
      }

      // On ajoute la journée au graphique seulement s'il y a eu des résultats
      // (Pour éviter d'avoir des barres à 0€ pour les jours futurs)
      const hasResults = bets.some(b => b.is_processed);
      if (hasResults) {
        dailyResults.push({ date, profit: dayProfit });
        globalProfit += dayProfit;
      }
    });

    // Tri inverse pour l'affichage liste (plus récent en haut)
    allCombos.sort((a, b) => new Date(b.date) - new Date(a.date));

    setSimulation({
      daily: dailyResults,
      totalProfit: globalProfit,
      avgProfit: dailyResults.length > 0 ? globalProfit / dailyResults.length : 0,
      comboList: allCombos
    });
  };

  // --- COMPOSANTS UI ---
  const StatusBadge = ({ status }) => {
    const styles = {
      WIN: "bg-green-500/20 text-green-400 border-green-500/50",
      LOSS: "bg-red-500/20 text-red-400 border-red-500/50",
      PENDING: "bg-yellow-500/20 text-yellow-400 border-yellow-500/50",
      VOID: "bg-slate-500/20 text-slate-400 border-slate-500/50"
    };
    // Fallback si status est null
    const st = status || "PENDING"; 
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-bold border ${styles[st] || styles.PENDING}`}>
        {st}
      </span>
    );
  };

  return (
    <div className="flex flex-col gap-6 p-4 pb-20">
      
      {/* HEADER & FILTRES */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 dark:text-white">Performance Center</h1>
          <p className="text-slate-500 text-sm">Analysez vos gains passés et suivez vos paris en cours.</p>
        </div>
        
        <div className="flex flex-wrap gap-3 items-center bg-white dark:bg-slate-900 p-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          {/* Date Picker */}
          <div className="flex items-center gap-2 px-2">
            <span className="text-slate-500 text-xs font-bold uppercase">Date :</span>
            <input 
              type="date" 
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="bg-slate-100 dark:bg-slate-800 border-none rounded-md text-sm py-1 px-2 text-slate-700 dark:text-white focus:ring-2 focus:ring-primary"
            />
            {selectedDate && (
              <button 
                onClick={() => setSelectedDate('')}
                className="text-xs text-red-400 hover:text-red-300 underline"
              >
                Reset (Tout)
              </button>
            )}
          </div>

          <div className="w-px h-6 bg-slate-700 mx-1"></div>

          {/* Tabs */}
          <div className="flex gap-1">
            <button 
              onClick={() => setActiveTab('history')}
              className={`px-3 py-1.5 rounded-lg text-sm font-bold transition-all ${activeTab === 'history' ? 'bg-slate-800 text-white shadow' : 'text-slate-500 hover:bg-slate-800/50'}`}
            >
              Paris Simples
            </button>
            <button 
              onClick={() => setActiveTab('simulation')}
              className={`px-3 py-1.5 rounded-lg text-sm font-bold transition-all ${activeTab === 'simulation' ? 'bg-primary text-white shadow' : 'text-slate-500 hover:bg-slate-800/50'}`}
            >
              Simu Combinés
            </button>
          </div>
        </div>
      </div>

      {/* --- ONGLET 1 : HISTORIQUE PARIS SIMPLES --- */}
      {activeTab === 'history' && (
        <div className="flex flex-col gap-6 animate-in fade-in duration-500">
          
          {/* Tableau */}
          <div className="bg-white dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-xl">
            <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
              <h3 className="font-bold text-white flex items-center gap-2">
                <span className="material-symbols-outlined text-blue-400">history_edu</span>
                {selectedDate ? `Paris du ${selectedDate}` : "Historique Complet"}
              </h3>
              <span className="text-xs bg-slate-800 px-2 py-1 rounded text-slate-400">
                {filteredData.length} paris trouvés
              </span>
            </div>
            
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm text-left text-slate-400">
                <thead className="bg-slate-950 text-xs uppercase font-medium text-slate-500">
                  <tr>
                    <th className="px-6 py-3">Date</th>
                    <th className="px-6 py-3">Rencontre</th>
                    <th className="px-6 py-3">Votre Pari</th>
                    <th className="px-6 py-3 text-center">Résultat</th>
                    <th className="px-6 py-3 text-right">Profit (1U)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {filteredData.map((bet) => (
                    <tr key={bet.id} className={`hover:bg-white/5 transition-colors ${!bet.is_processed ? 'bg-blue-500/5' : ''}`}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {bet.match_date}
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-bold text-white">{bet.home_team} vs {bet.away_team}</div>
                        <div className="text-xs text-slate-500">Confiance: {bet.confidence_score}%</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-bold border ${
                          bet.bet_type === 'OVER' 
                            ? 'bg-green-900/20 text-green-400 border-green-900/50' 
                            : 'bg-red-900/20 text-red-400 border-red-900/50'
                        }`}>
                          {bet.bet_type} {bet.fdj_line}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        {/* Si pas processé, c'est en attente */}
                        <StatusBadge status={bet.is_processed ? bet.bet_result : "PENDING"} />
                        {bet.actual_score && <div className="text-xs mt-1 text-slate-500">Score: {bet.actual_score}</div>}
                      </td>
                      <td className={`px-6 py-4 text-right font-mono font-bold text-base ${
                        !bet.is_processed ? 'text-slate-600' : 
                        bet.payout > 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {!bet.is_processed ? '...' : (bet.payout > 0 ? '+' : '') + bet.payout?.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                  {filteredData.length === 0 && (
                    <tr><td colSpan="5" className="p-10 text-center text-slate-500 italic">Aucun pari trouvé pour cette période.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* --- ONGLET 2 : SIMULATION COMBINÉS --- */}
      {activeTab === 'simulation' && (
        <div className="flex flex-col gap-6 animate-in fade-in duration-500">
          
          {/* KPIs Simulation */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
              <p className="text-slate-400 text-xs font-bold uppercase mb-1">Mise Totale</p>
              <div className="flex items-center gap-3">
                <input 
                  type="number" 
                  value={stake} 
                  onChange={(e) => setStake(Number(e.target.value))}
                  className="w-24 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white font-mono"
                />
                <span className="text-slate-500">€ par combiné</span>
              </div>
            </div>
            <div className={`p-5 rounded-xl border ${simulation.totalProfit >= 0 ? 'bg-green-900/20 border-green-900/50' : 'bg-red-900/20 border-red-900/50'}`}>
              <p className="text-slate-400 text-xs font-bold uppercase mb-1">Profit Total {selectedDate ? '(Filtré)' : '(Global)'}</p>
              <p className={`text-3xl font-black ${simulation.totalProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {simulation.totalProfit > 0 ? '+' : ''}{simulation.totalProfit.toFixed(2)} €
              </p>
            </div>
            <div className="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
              <p className="text-slate-400 text-xs font-bold uppercase mb-1">Moyenne / Jour</p>
              <p className="text-3xl font-black text-blue-400">
                {simulation.avgProfit > 0 ? '+' : ''}{simulation.avgProfit.toFixed(2)} €
              </p>
            </div>
          </div>

          {/* Graphique (Uniquement si pas de filtre date unique, sinon c'est peu utile) */}
          {!selectedDate && (
            <div className="h-64 bg-white dark:bg-slate-900/50 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={simulation.daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f1f5f9' }}
                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                  />
                  <ReferenceLine y={0} stroke="#475569" />
                  <Bar dataKey="profit" fill="#2b7cee" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Liste des Combinés */}
          <div className="bg-white dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-900/50">
              <h3 className="font-bold text-white">Détail des Tickets (2 Matchs)</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm text-left text-slate-400">
                <thead className="bg-slate-950 text-xs uppercase font-medium text-slate-500">
                  <tr>
                    <th className="px-6 py-3">Date</th>
                    <th className="px-6 py-3">Sélection</th>
                    <th className="px-6 py-3 text-center">Cote Totale</th>
                    <th className="px-6 py-3 text-center">Statut</th>
                    <th className="px-6 py-3 text-right">Gains</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {simulation.comboList.map((combo) => (
                    <tr key={combo.id} className="hover:bg-white/5 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">{combo.date}</td>
                      <td className="px-6 py-4">
                        <div className="flex flex-col gap-2">
                          {combo.matches.map((m, idx) => (
                            <div key={idx} className="flex items-center gap-2 text-xs text-slate-300">
                              <span className={`size-2 rounded-full ${
                                m.bet_result === 'WIN' ? 'bg-green-500' : 
                                m.bet_result === 'LOSS' ? 'bg-red-500' : 'bg-yellow-500'
                              }`}></span>
                              <span>{m.home_team}/{m.away_team}</span>
                              <span className="text-slate-500">({m.bet_type} {m.fdj_line})</span>
                            </div>
                          ))}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center font-mono text-yellow-500 font-bold">
                        {combo.totalOdd}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <StatusBadge status={combo.status} />
                      </td>
                      <td className={`px-6 py-4 text-right font-mono font-bold text-base ${
                        combo.status === 'PENDING' ? 'text-slate-600' :
                        Number(combo.profit) > 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {combo.status === 'PENDING' ? '...' : (Number(combo.profit) > 0 ? '+' : '') + combo.profit + ' €'}
                      </td>
                    </tr>
                  ))}
                  {simulation.comboList.length === 0 && (
                    <tr><td colSpan="5" className="p-10 text-center text-slate-500 italic">Pas assez de paris "Best Bets" sur cette période pour créer des combinés.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}
    </div>
  );
};

export default Analytics;