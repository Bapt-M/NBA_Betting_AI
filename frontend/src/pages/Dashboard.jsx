import React, { useEffect, useState } from 'react';
import axios from 'axios';

const Dashboard = () => {
  // State pour les données (simulées ici pour l'exemple UI, à connecter à l'API)
  const [stats, setStats] = useState({ winRate: "58.7%", avgError: "+/- 4.2 pts", profit: "+12.5 Units" });
  const [results, setResults] = useState([]);

  useEffect(() => {
    // Fetch API data here
    // axios.get('/api/results/latest').then(res => setResults(res.data));
    
    // Mock data based on your HTML
    setResults([
      { id: "22300401", match: "LAL @ BOS", pred: 228.5, conf: "95%", line: 225.5, actual: 230, res: "Win", perf: "+1.00" },
      { id: "22300402", match: "MIA @ DEN", pred: 212.0, conf: "88%", line: 215.0, actual: 208, res: "Loss", perf: "-1.00" },
      { id: "22300403", match: "GSW @ PHX", pred: 235.5, conf: "92%", line: 235.5, actual: 231, res: "Push", perf: "0.00" },
    ]);
  }, []);

  // Visualisation simplifiée pour l'histogramme d'erreur
  const errorDistribution = [15, 18, 25, 30, 40, 55, 60, 70, 75, 85, 95, 90, 80, 72, 65, 50, 42, 35, 20, 10];

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-wrap justify-between gap-3 p-4">
        <p className="text-slate-900 dark:text-white text-4xl font-black leading-tight tracking-[-0.033em]">Performance Dashboard</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-4">
        {/* KPIs */}
        <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard title="Win Rate" value={stats.winRate} />
          <StatCard title="Average Error" value={stats.avgError} />
          <StatCard title="Simulated Profit" value={stats.profit} isGreen />
        </div>

        {/* Error Chart */}
        <div className="lg:col-span-3 flex flex-col gap-4 rounded-xl border border-slate-200 dark:border-slate-800 p-6 bg-white dark:bg-slate-900/50">
          <div>
            <p className="text-lg font-bold dark:text-white">Prediction Error Distribution</p>
            <p className="text-sm text-slate-500">Frequency of prediction errors across 20 bins</p>
          </div>
          <div className="grid min-h-[220px] grid-flow-col gap-2 items-end px-3">
            {errorDistribution.map((height, i) => (
              <div key={i} className="flex flex-col items-center gap-2 group h-full justify-end">
                <div 
                  className="bg-primary/20 group-hover:bg-primary/40 rounded-t w-full transition-all duration-300" 
                  style={{ height: `${height}%` }}
                ></div>
                <p className="text-xs text-slate-500 font-medium">{i - 10 > 0 ? `+${i-10}` : i-10}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Results Table */}
        <div className="lg:col-span-3 flex flex-col gap-4">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-2xl font-bold dark:text-white">Match Results Breakdown</h2>
            <input 
              className="rounded-lg border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 py-2 px-4 text-white w-64"
              placeholder="Filter matches..."
            />
          </div>
          
          <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50">
            <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800 text-sm">
              <thead className="bg-slate-100/50 dark:bg-slate-800/20 text-slate-500">
                <tr>
                  {["Match ID", "Teams", "Predicted", "Conf", "Line", "Actual", "Result", "Perf"].map(h => (
                    <th key={h} className="px-6 py-3 text-left font-medium uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {results.map((row, i) => (
                  <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-6 py-4 font-mono text-slate-500">{row.id}</td>
                    <td className="px-6 py-4 font-medium dark:text-white">{row.match}</td>
                    <td className="px-6 py-4 text-slate-300">{row.pred}</td>
                    <td className="px-6 py-4 text-slate-300">{row.conf}</td>
                    <td className="px-6 py-4 text-slate-300">{row.line}</td>
                    <td className="px-6 py-4 text-slate-300">{row.actual}</td>
                    <td className="px-6 py-4">
                      <Badge status={row.res} />
                    </td>
                    <td className={`px-6 py-4 font-medium ${row.perf.startsWith('+') ? 'text-green-400' : row.perf === '0.00' ? 'text-slate-400' : 'text-red-400'}`}>
                      {row.perf}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

// UI Helpers
const StatCard = ({ title, value, isGreen }) => (
  <div className="flex flex-col gap-2 rounded-xl p-6 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50">
    <p className="text-slate-600 dark:text-slate-300 font-medium">{title}</p>
    <p className={`text-3xl font-bold ${isGreen ? "text-green-500" : "dark:text-white"}`}>{value}</p>
  </div>
);

const Badge = ({ status }) => {
  const colors = {
    Win: "bg-green-900/50 text-green-300",
    Loss: "bg-red-900/50 text-red-300",
    Push: "bg-slate-700 text-slate-300"
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] || colors.Push}`}>
      {status}
    </span>
  );
};

export default Dashboard;