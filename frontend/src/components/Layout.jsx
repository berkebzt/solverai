import React from 'react';
import { MessageSquare, FileText, Settings, Cpu } from 'lucide-react';

const Layout = ({ children }) => {
  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar glass">
        <div className="flex items-center gap-3 mb-8 px-2">
          <div className="p-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500 animate-pulse-glow">
            <Cpu size={24} color="white" />
          </div>
          <h1 className="text-2xl brand-text">SOLVERAI</h1>
        </div>

        <nav className="flex flex-col gap-2">
          <NavItem icon={<MessageSquare size={20} />} label="Chat" active />
          <NavItem icon={<FileText size={20} />} label="Documents" />
          <NavItem icon={<Settings size={20} />} label="Settings" />
        </nav>

        <div className="mt-auto p-4 glass-panel rounded-xl">
          <p className="text-xs text-gray-400 mb-2">System Status</p>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span className="text-sm font-mono text-green-400">ONLINE</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

const NavItem = ({ icon, label, active }) => (
  <button className={`flex items-center gap-3 p-3 rounded-lg transition-all duration-300 ${
    active 
      ? 'bg-white/10 text-cyan-400 border-l-2 border-cyan-400' 
      : 'text-gray-400 hover:bg-white/5 hover:text-white'
  }`}>
    {icon}
    <span className="font-medium">{label}</span>
  </button>
);

export default Layout;
