import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import ProbeView from './components/ProbeView';
import DashboardView from './components/DashboardView';
import { Radio, LayoutDashboard } from 'lucide-react';

function Landing() {
  return (
    <div className="h-screen bg-background-dark text-white flex flex-col items-center justify-center p-6 relative overflow-hidden">
      <div className="absolute inset-0 bg-cyber-grid opacity-20 pointer-events-none"></div>

      <div className="mb-12 text-center z-10">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tighter mb-4">SPATIAL<span className="text-primary">VCS</span></h1>
        <p className="text-slate-400 max-w-md mx-auto font-mono text-xs md:text-sm tracking-widest uppercase">
          Unhindered Interface v2.1.0 // Select Operative Role
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8 w-full max-w-4xl z-10">
        <Link to="/probe" className="group relative block p-8 bg-surface-dark border border-slate-800 rounded-2xl hover:border-primary hover:shadow-[0_0_30px_rgba(0,240,255,0.15)] transition-all">
          <div className="absolute top-4 right-4 text-[10px] font-mono text-slate-600 border border-slate-800 px-2 py-1 rounded">MOBILE_CLIENT</div>
          <div className="w-16 h-16 bg-slate-800 rounded-xl mb-6 flex items-center justify-center group-hover:bg-primary group-hover:text-black transition-colors text-slate-400">
            <Radio className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold mb-2 group-hover:text-primary transition-colors">Deploy Probe</h2>
          <p className="text-slate-400 text-sm">Initiate field scanning sequence. Optimized for mobile device sensors (LiDAR/Camera).</p>
        </Link>

        <Link to="/dashboard" className="group relative block p-8 bg-surface-dark border border-slate-800 rounded-2xl hover:border-primary hover:shadow-[0_0_30px_rgba(0,240,255,0.15)] transition-all">
          <div className="absolute top-4 right-4 text-[10px] font-mono text-slate-600 border border-slate-800 px-2 py-1 rounded">WORKSTATION</div>
          <div className="w-16 h-16 bg-slate-800 rounded-xl mb-6 flex items-center justify-center group-hover:bg-primary group-hover:text-black transition-colors text-slate-400">
            <LayoutDashboard className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold mb-2 group-hover:text-primary transition-colors">Access Dashboard</h2>
          <p className="text-slate-400 text-sm">Enter the command center. Manage repositories, merge spatial branches, and analyze 3D semantic data.</p>
        </Link>
      </div>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/probe" element={<ProbeView />} />
        <Route path="/dashboard" element={<DashboardView />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
