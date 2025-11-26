import React from 'react';
import { MessageSquare, FileText, Settings, Cpu } from 'lucide-react';

const Layout = ({ children }) => {
  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Cpu size={22} color="white" />
          </div>
          <span className="brand-text">SOLVERAI</span>
        </div>

        <nav className="nav-items">
          <NavItem icon={<MessageSquare size={18} />} label="Chat" active />
          <NavItem icon={<FileText size={18} />} label="Documents" />
          <NavItem icon={<Settings size={18} />} label="Settings" />
        </nav>

        <div className="status-card">
          <div className="status-label">System Status</div>
          <div className="status-indicator">
            <div className="status-dot" />
            <span className="status-text">ONLINE</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

const NavItem = ({ icon, label, active }) => (
  <button className={`nav-item ${active ? 'active' : ''}`}>
    {icon}
    <span>{label}</span>
  </button>
);

export default Layout;
