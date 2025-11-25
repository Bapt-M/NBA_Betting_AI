import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { getTeamName } from '../teamMapping';

const Dashboard = () => {
  const [stats, setStats] = useState({ winRate: "0%", avgError: "0 pts", profit: "0 U" });
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const resResults = await axios.get('http://localhost:8000/api/results/latest?limit=10');
        setResults(resResults.data);

        const resStats = await axios.get('http://localhost:8000/api/analytics/roi');
        if (resStats.data.summary) {
          const s = resStats.data.summary;
          setStats({
            winRate: `${s.win_rate}%`,
            avgError: "+/- 4.5", 
            profit: `${s.profit_net > 0 ? '+' : ''}${s.profit_net.toFixed(1)} Units`
          });
        }
        setLoading(false);
      } catch (err) {
        console.error("Erreur dashboard", err);
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div className="p-10 text-center text-white">Chargement...</div>;

  return (
    <div className="flex flex-col gap-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-4">
        <StatCard title="Win Rate (Global)" value={stats.winRate} />
        <StatCard title="Net Profit" value={stats.profit} isGreen={stats.profit.includes('+')} />
        <StatCard title="Total Bets Analyzed" value={results.length} />
      </div>

      {/* Results Table */}
      <div className="flex flex-col gap-4 px-4">
        <h2 className="text-2xl font-bold dark:text-white">Derniers Résultats NBA</h2>
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800 text-sm">
            <thead className="bg-slate-100/50 dark:bg-slate-800/20 text-slate-500">
              <tr>
                <th className="px-6 py-3 text-left font-medium uppercase">Date</th>
                <th className="px-6 py-3 text-left font-medium uppercase">Match</th>
                <th className="px-6 py-3 text-left font-medium uppercase">Score Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {results.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                  <td className="px-6 py-4 text-slate-500">{new Date(row.date).toLocaleDateString()}</td>
                  <td className="px-6 py-4 font-medium dark:text-white">
                    {getTeamName(row.home_team)} <span className="text-slate-500">vs</span> {getTeamName(row.away_team)}
                  </td>
                  <td className="px-6 py-4 text-slate-300 font-mono font-bold text-lg">
                    {row.actual_total} pts
                  </td>
                </tr>
              ))}
              {results.length === 0 && (
                <tr><td colSpan="3" className="p-6 text-center text-slate-500">Aucun résultat récent.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ title, value, isGreen }) => (
  <div className="flex flex-col gap-2 rounded-xl p-6 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50">
    <p className="text-slate-600 dark:text-slate-300 font-medium">{title}</p>
    <p className={`text-3xl font-bold ${isGreen ? "text-green-500" : "dark:text-white"}`}>{value}</p>
  </div>
);

export default Dashboard;