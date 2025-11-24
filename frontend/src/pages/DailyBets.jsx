import React, { useState, useEffect } from 'react';

const DailyBets = () => {
  const [predictions, setPredictions] = useState([]);

  useEffect(() => {
    // Mock API call
    setPredictions([
      { time: "19:30 EST", teams: "BKN @ CLE", pred: 224.5, line: 220.5, rec: "OVER 220.5", conf: "High", val: "+4.2%", form: ["W","L","W","W","L"] },
      { time: "20:00 EST", teams: "BOS @ MIL", pred: 217.0, line: 218.5, rec: "UNDER 218.5", conf: "Medium", val: "+1.8%", form: ["W","W","W","W","L"] },
      { time: "22:30 EST", teams: "PHX @ LAL", pred: 230.5, line: 232.0, rec: "UNDER 232.0", conf: "Low", val: "-0.5%", form: ["W","L","L","W","W"] },
    ]);
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap justify-between gap-3 p-4">
        <p className="text-slate-900 dark:text-white text-4xl font-black">Daily NBA Predictions</p>
      </div>

      {/* Filters */}
      <div className="flex flex-col lg:flex-row gap-4 justify-between items-center p-4 border-y border-slate-800">
        <div className="w-full lg:w-1/3 flex flex-col gap-2">
          <div className="flex justify-between text-sm text-white">
            <span>Confidence Threshold</span>
            <span>75%</span>
          </div>
          <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full bg-primary w-3/4"></div>
          </div>
        </div>
        
        <div className="flex gap-3">
          <button className="bg-primary text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-600 transition-colors">
            <span className="material-symbols-outlined text-sm">download</span> Export
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/50">
        <table className="min-w-full divide-y divide-slate-800 text-sm">
          <thead className="bg-slate-800/50 text-slate-400">
            <tr>
              {["Time", "Teams", "Recent Form", "Predicted", "FDJ Line", "Recommendation", "Confidence", "EV"].map(h => (
                <th key={h} className="px-6 py-3 text-left uppercase font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-white">
            {predictions.map((row, i) => (
              <tr key={i} className="hover:bg-white/5 transition-colors">
                <td className="px-6 py-4 text-slate-400">{row.time}</td>
                <td className="px-6 py-4 font-medium">{row.teams}</td>
                <td className="px-6 py-4">
                  <div className="flex gap-1">
                    {row.form.map((res, j) => (
                      <span key={j} className={`size-3 rounded-full ${res === 'W' ? 'bg-green-500' : 'bg-red-500'}`}></span>
                    ))}
                  </div>
                </td>
                <td className="px-6 py-4 font-mono">{row.pred}</td>
                <td className="px-6 py-4 text-slate-400">{row.line}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs font-bold ${row.rec.includes("OVER") ? "bg-green-900/50 text-green-300" : "bg-red-900/50 text-red-300"}`}>
                    {row.rec}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs font-bold ${
                    row.conf === "High" ? "bg-green-900 text-green-300" :
                    row.conf === "Medium" ? "bg-yellow-900 text-yellow-300" :
                    "bg-slate-700 text-slate-300"
                  }`}>
                    {row.conf}
                  </span>
                </td>
                <td className={`px-6 py-4 font-medium ${row.val.startsWith('-') ? 'text-red-400' : 'text-green-400'}`}>
                  {row.val}
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