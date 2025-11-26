import React from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

const Layout = () => {
  const location = useLocation();
  const isActive = (path) => location.pathname === path ? "text-primary" : "text-slate-500 dark:text-slate-400 hover:text-primary dark:hover:text-primary";

  return (
    <div className="relative flex h-auto min-h-screen w-full flex-col bg-background-light dark:bg-background-dark overflow-x-hidden">
      {/* TopNavBar */}
      <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-slate-200/10 dark:border-slate-800 px-6 sm:px-10 py-3 bg-white dark:bg-[#101822]">
        <div className="flex items-center gap-4 text-slate-900 dark:text-white">
          <div className="size-6 text-primary">
            <svg fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
              <path d="M44 4H30.6666V17.3334H17.3334V30.6666H4V44H44V4Z" fill="currentColor"></path>
            </svg>
          </div>
          <h2 className="text-lg font-bold leading-tight tracking-[-0.015em]">NBA Betting Dashboard</h2>
        </div>
        
        <div className="hidden md:flex flex-1 justify-center gap-8">
          <div className="flex items-center gap-9">
            <Link to="/" className={`text-sm font-medium leading-normal ${isActive('/')}`}>Dashboard</Link>
            <Link to="/daily-bets" className={`text-sm font-medium leading-normal ${isActive('/daily-bets')}`}>Daily Bets</Link>
            <Link to="/simulation" className={`text-sm font-medium leading-normal ${isActive('/simulation')}`}>Simulation</Link>
            <Link to="/settings" className={`text-sm font-medium leading-normal ${isActive('/settings')}`}>Settings</Link>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button className="flex h-10 w-10 cursor-pointer items-center justify-center overflow-hidden rounded-full bg-slate-200/50 dark:bg-slate-800 text-slate-900 dark:text-white">
            <span className="material-symbols-outlined text-sm font-bold">notifications</span>
          </button>
          <div className="bg-center bg-no-repeat aspect-square bg-cover rounded-full size-10 bg-slate-700">
             {/* Placeholder Profile */}
             <span className="flex items-center justify-center h-full text-xs font-bold text-white">AI</span>
          </div>
        </div>
      </header>

      <main className="flex-1 px-4 sm:px-6 md:px-10 lg:px-20 xl:px-40 py-8">
        <div className="layout-content-container flex flex-col max-w-7xl mx-auto w-full">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;