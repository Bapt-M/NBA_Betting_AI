import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Settings = () => {
  const [status, setStatus] = useState(null);
  const [loadingTask, setLoadingTask] = useState({});

  // Fetch System Status on Load
  const fetchStatus = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/system/status');
      setStatus(res.data);
    } catch (err) {
      console.error("API Error", err);
    }
  };

  useEffect(() => { fetchStatus(); }, []);

  const triggerTask = async (taskName) => {
    setLoadingTask(prev => ({ ...prev, [taskName]: true }));
    try {
      await axios.post(`http://localhost:8000/api/tasks/trigger/${taskName}`);
      // Petit délai pour laisser le temps au backend de changer d'état si besoin
      setTimeout(fetchStatus, 2000);
    } catch (e) {
      alert("Erreur lancement tâche");
    } finally {
      setLoadingTask(prev => ({ ...prev, [taskName]: false }));
    }
  };

  // Composant Indicateur
  const StatusItem = ({ label, value, valid, subtext }) => (
    <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/10">
      <div>
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
        <div className="flex items-center gap-2">
          <span className={`size-2 rounded-full ${valid ? 'bg-green-500' : 'bg-red-500'}`}></span>
          <p className="text-lg font-bold text-slate-900 dark:text-white">{value}</p>
        </div>
      </div>
      {subtext && <p className="text-xs text-slate-400">{subtext}</p>}
    </div>
  );

  return (
    <div className="flex flex-col gap-6 p-4">
      <h1 className="text-3xl font-black text-slate-900 dark:text-white">System Settings</h1>

      {/* STATUS CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatusItem 
          label="Raw Data" 
          value={status?.data.raw_rows.toLocaleString() || "0"} 
          valid={status?.data.raw_rows > 0}
          subtext="Rows in CSV"
        />
        <StatusItem 
          label="Processed Data" 
          value={status?.data.processed_rows.toLocaleString() || "0"} 
          valid={status?.data.processed_rows > 0}
          subtext="Rows in Database"
        />
        <StatusItem 
          label="Data Freshness" 
          value={status?.data.last_update || "Never"} 
          valid={status?.data.is_up_to_date}
          subtext={status?.data.is_up_to_date ? "Up to Date" : "Outdated"}
        />
        <StatusItem 
          label="Model Health" 
          value={status?.model.exists ? `MAE: ${status.model.mae}` : "No Model"} 
          valid={status?.model.exists}
          subtext={status?.model.last_trained ? new Date(status.model.last_trained).toLocaleDateString() : "Never trained"}
        />
      </div>

      {/* CONTROL ACTIONS */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-900/50 p-6 rounded-xl border border-slate-200 dark:border-slate-800">
          <h3 className="text-xl font-bold mb-4 dark:text-white">Data Pipeline</h3>
          <div className="space-y-3">
            <ActionButton 
              label="1. Fetch Raw Data" 
              loading={loadingTask['fetch_data']} 
              onClick={() => triggerTask('fetch_data')} 
            />
            <ActionButton 
              label="2. Process Features" 
              loading={loadingTask['process_data']} 
              onClick={() => triggerTask('process_data')} 
            />
            <ActionButton 
              label="3. Train Model" 
              loading={loadingTask['train_model']} 
              onClick={() => triggerTask('train_model')} 
            />
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900/50 p-6 rounded-xl border border-slate-200 dark:border-slate-800">
          <h3 className="text-xl font-bold mb-4 dark:text-white">Daily Operations</h3>
          <div className="space-y-3">
            <ActionButton 
              label="Scrape FDJ Odds" 
              loading={loadingTask['scrape_odds']} 
              onClick={() => triggerTask('scrape_odds')} 
              color="bg-indigo-600 hover:bg-indigo-700"
            />
            <ActionButton 
              label="Generate Predictions" 
              loading={loadingTask['predict_daily']} 
              onClick={() => triggerTask('predict_daily')} 
              color="bg-purple-600 hover:bg-purple-700"
            />
            <ActionButton 
              label="Update History & Eval" 
              loading={loadingTask['update_history']} 
              onClick={() => triggerTask('update_history')} 
              color="bg-yellow-600 hover:bg-yellow-700"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

const ActionButton = ({ label, onClick, loading, color = "bg-slate-700 hover:bg-slate-600" }) => (
  <button 
    onClick={onClick} 
    disabled={loading}
    className={`w-full py-3 px-4 rounded-lg text-white font-medium transition-all flex justify-center items-center gap-2 ${color} ${loading ? 'opacity-50' : ''}`}
  >
    {loading && <span className="animate-spin material-symbols-outlined text-sm">progress_activity</span>}
    {label}
  </button>
);

export default Settings;