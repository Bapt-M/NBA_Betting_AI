import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { getTeamName } from '../teamMapping';

const Analytics = () => {
  const [data, setData] = useState([]); 
  const [filteredData, setFilteredData] = useState([]);
  const [simulation, setSimulation] = useState({ daily: [], totalProfit: 0, potentialProfit: 0, comboList: [] });
  
  const [stake, setStake] = useState(10);
  const [activeTab, setActiveTab] = useState('history');
  const [selectedDate, setSelectedDate] = useState('');

  useEffect(() => { fetchAllData(); }, []);
  useEffect(() => { applyFilters(); }, [data, selectedDate]);
  useEffect(() => { if (filteredData.length > 0) runSimulation(); }, [filteredData, stake]);

  const fetchAllData = async () => {
    try {
      const resH = await axios.get('http://localhost:8000/api/predictions/history');
      const resP = await axios.get('http://localhost:8000/api/predictions/today');
      const all = [...resP.data, ...resH.data];

      // DÉDUPLICATION
      const bestBetsMap = {};
      all.forEach(pred => {
        const key = `${pred.match_date}-${pred.home_team}-${pred.away_team}`;
        if (!bestBetsMap[key] || pred.confidence_score > bestBetsMap[key].confidence_score) {
          bestBetsMap[key] = pred;
        }
      });

      const sorted = Object.values(bestBetsMap).sort((a, b) => {
         if (a.is_processed === b.is_processed) return new Date(b.match_date) - new Date(a.match_date);
         return a.is_processed ? 1 : -1; 
      });
      setData(sorted);
    } catch (e) { console.error(e); }
  };

  const applyFilters = () => {
    setFilteredData(selectedDate ? data.filter(d => d.match_date === selectedDate) : data);
  };

  const runSimulation = () => {
    const byDate = filteredData.reduce((acc, b) => {
      if (!acc[b.match_date]) acc[b.match_date] = [];
      acc[b.match_date].push(b);
      return acc;
    }, {});

    const combos = [];
    let totalProfit = 0, potentialProfit = 0;
    const dailyRes = [];

    Object.keys(byDate).sort().forEach(date => {
      const bets = byDate[date].sort((a, b) => b.confidence_score - a.confidence_score);
      let dayProfit = 0;

      for (let i = 0; i < bets.length; i += 2) {
        const b1 = bets[i];
        const b2 = bets[i+1];
        
        let matches = [b1];
        let oddTotal = b1.odd || 1.90;
        
        if (b2) {
            matches.push(b2);
            oddTotal *= (b2.odd || 1.90);
        }

        const potentialWin = (stake * oddTotal) - stake;
        let status = "PENDING";
        let profit = 0;
        let isPotential = false;

        const allProcessed = matches.every(m => m.is_processed);
        const anyLoss = matches.some(m => m.bet_result === 'LOSS');
        
        if (anyLoss) { status = "LOSS"; profit = -stake; }
        else if (!allProcessed) { status = "PENDING"; profit = potentialWin; isPotential = true; }
        else { status = "WIN"; profit = potentialWin; }

        if (isPotential) potentialProfit += profit;
        else dayProfit += profit;

        combos.push({
            id: `c-${date}-${i}`, date, matches, 
            odd: oddTotal.toFixed(2), status, 
            profit: profit.toFixed(2), isPotential
        });
      }

      if (bets.some(b => b.is_processed)) {
          dailyRes.push({ date, profit: dayProfit });
          totalProfit += dayProfit;
      }
    });

    setSimulation({ daily: dailyRes, totalProfit, potentialProfit, comboList: combos.reverse() });
  };

  const Badge = ({ status }) => {
    const color = { WIN: "text-green-400 bg-green-900/20", LOSS: "text-red-400 bg-red-900/20", PENDING: "text-yellow-400 bg-yellow-900/20" }[status] || "text-slate-400";
    return <span className={`px-2 py-0.5 rounded text-xs font-bold ${color} border border-white/10`}>{status}</span>;
  };

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-black text-white">Analytics & Simulation</h1>
        <input type="date" value={selectedDate} onChange={e => setSelectedDate(e.target.value)} className="bg-slate-800 border-none rounded text-white" />
      </div>

      {/* ONGLETS */}
      <div className="flex gap-2 border-b border-slate-800 pb-1">
         <button onClick={() => setActiveTab('history')} className={`px-4 py-2 text-sm font-bold ${activeTab==='history'?'text-primary border-b-2 border-primary':'text-slate-500'}`}>Historique Paris</button>
         <button onClick={() => setActiveTab('simulation')} className={`px-4 py-2 text-sm font-bold ${activeTab==='simulation'?'text-primary border-b-2 border-primary':'text-slate-500'}`}>Simulation Combinés</button>
      </div>

      {activeTab === 'history' && (
        <div className="bg-slate-900/50 rounded-xl border border-slate-800 overflow-hidden">
          <table className="w-full text-sm text-left text-slate-400">
            <thead className="bg-slate-950 text-xs uppercase">
              <tr>
                <th className="px-6 py-3">Date</th>
                <th className="px-6 py-3">Match</th>
                <th className="px-6 py-3">Pari</th>
                <th className="px-6 py-3 text-right">Cote</th>
                <th className="px-6 py-3 text-right">Confiance</th> {/* Alignement à droite */}
                <th className="px-6 py-3 text-center">Résultat</th>
                <th className="px-6 py-3 text-right">Profit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {filteredData.map(bet => (
                <tr key={bet.id} className="hover:bg-white/5">
                  <td className="px-6 py-4">{bet.match_date}</td>
                  <td className="px-6 py-4 text-white font-bold">{getTeamName(bet.home_team)} vs {getTeamName(bet.away_team)}</td>
                  <td className="px-6 py-4"><span className="text-primary font-bold">{bet.bet_type} {bet.fdj_line}</span></td>
                  <td className="px-6 py-4 text-right font-mono">{bet.odd ? bet.odd.toFixed(2) : '-'}</td>
                  
                  {/* BARRE DE CONFIANCE MODIFIÉE */}
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${bet.confidence_score > 80 ? 'bg-green-500' : bet.confidence_score > 50 ? 'bg-blue-500' : 'bg-slate-400'}`} 
                          style={{ width: `${Math.min(bet.confidence_score, 100)}%` }}
                        ></div>
                      </div>
                      <span className="w-8 text-right text-xs font-bold">{bet.confidence_score}%</span>
                      {bet.recommendation === 'Best Bet' && <span className="text-yellow-500 text-xs">★</span>}
                    </div>
                  </td>
                  {/* FIN MODIFICATION */}

                  <td className="px-6 py-4 text-center"><Badge status={bet.is_processed ? bet.bet_result : "PENDING"} /></td>
                  <td className={`px-6 py-4 text-right font-mono font-bold text-base ${
                        !bet.is_processed ? 'text-slate-600' : 
                        bet.payout > 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                     {!bet.is_processed ? '...' : (bet.payout > 0 ? '+' : '') + (bet.payout ? bet.payout.toFixed(2) : '0.00')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'simulation' && (
        <div className="flex flex-col gap-6">
            <div className="grid grid-cols-3 gap-4">
                <div className="bg-slate-800 p-4 rounded-lg">
                    <p className="text-xs text-slate-400 uppercase">Mise / Ticket</p>
                    <input type="number" value={stake} onChange={e => setStake(Number(e.target.value))} className="bg-transparent text-2xl font-bold text-white w-full focus:outline-none" />
                </div>
                <div className="bg-slate-800 p-4 rounded-lg">
                    <p className="text-xs text-slate-400 uppercase">Profit Réalisé</p>
                    <p className={`text-2xl font-bold ${simulation.totalProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>{simulation.totalProfit.toFixed(2)} €</p>
                </div>
                <div className="bg-slate-800 p-4 rounded-lg border border-yellow-500/30">
                    <p className="text-xs text-yellow-500 uppercase">Potentiel En Cours</p>
                    <p className="text-2xl font-bold text-yellow-400">{simulation.potentialProfit.toFixed(2)} €</p>
                </div>
            </div>

            <div className="bg-slate-900/50 rounded-xl border border-slate-800 overflow-hidden">
                <table className="w-full text-sm text-left text-slate-400">
                    <thead className="bg-slate-950 text-xs uppercase">
                        <tr><th className="px-6 py-3">Date</th><th className="px-6 py-3">Ticket</th><th className="px-6 py-3 text-center">Cote Totale</th><th className="px-6 py-3 text-center">Statut</th><th className="px-6 py-3 text-right">Gains</th></tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        {simulation.comboList.map(c => (
                            <tr key={c.id} className="hover:bg-white/5">
                                <td className="px-6 py-4">{c.date}</td>
                                <td className="px-6 py-4">
                                    {c.matches.map((m, i) => (
                                        <div key={i} className="flex items-center gap-2 mb-1">
                                            <div className={`size-2 rounded-full ${m.bet_result==='WIN'?'bg-green-500':m.bet_result==='LOSS'?'bg-red-500':'bg-yellow-500'}`}></div>
                                            <span className="text-white">{getTeamName(m.home_team)}/{getTeamName(m.away_team)}</span>
                                            <span className="text-xs text-slate-500">({m.bet_type} {m.fdj_line} @ {m.odd})</span>
                                        </div>
                                    ))}
                                </td>
                                <td className="px-6 py-4 text-center font-mono text-yellow-500">{c.odd}</td>
                                <td className="px-6 py-4 text-center"><Badge status={c.status} /></td>
                                <td className={`px-6 py-4 text-right font-bold ${c.isPotential ? 'text-yellow-400' : Number(c.profit)>0 ? 'text-green-400' : 'text-red-400'}`}>{c.isPotential ? '(Pot)' : ''} {c.profit} €</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
      )}
    </div>
  );
};
export default Analytics;