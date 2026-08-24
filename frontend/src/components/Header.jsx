import React from 'react';
import { ShieldAlert, Clock, CheckCircle2, TrendingUp, AlertTriangle, Layers } from 'lucide-react';
import { evaluationData } from '../data/evaluationData';

export default function Header({ activeTab, setActiveTab }) {
  const h = evaluationData.held_out;
  const nCases = evaluationData.held_out.caught + evaluationData.held_out.n_false_positives;
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'threats', label: 'Threat models' },
    { id: 'signals', label: 'Signal engine' },
    { id: 'cases', label: `Case files (${nCases})` },
    { id: 'economics', label: 'Unit economics' },
  ];

  return (
    <header className="border-b border-slate-800 bg-[#080e1e]/90 backdrop-blur sticky top-0 z-50">
      {/* Top Regulatory / Program Context Bar */}
      <div className="bg-slate-950/80 border-b border-slate-800/80 px-6 py-2">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="bg-blue-500/10 text-blue-300 font-medium px-2 py-0.5 rounded border border-blue-500/25">
              Razorpay AI Buildathon — Track 02 (AI Risk Manager)
            </span>
            <span className="text-slate-400 hidden sm:inline">•</span>
            <span className="text-slate-300 hidden sm:inline font-medium">Continuous Merchant-Drift Detection for Indian PAs</span>
          </div>
          <div className="flex items-center gap-4 text-slate-300">
            <div className="flex items-center gap-1.5 text-slate-400">
              <Clock className="w-3.5 h-3.5" />
              <span>Mastercard SMMP: <strong className="font-semibold text-slate-200">72h clock</strong></span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>RBI PA Directions 2025: <strong className="font-semibold text-slate-200">ongoing consistency</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Header */}
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-blue-950/50 border border-blue-400/30">
              <ShieldAlert className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-white tracking-tight">DriftWatch</h1>
                <span className="text-[10px] font-mono font-medium uppercase tracking-wide bg-slate-800/80 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                  Synthetic replay &middot; seed 20260823 &middot; full signal set
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Lead-Time Evaluated • Peer-Relative Velocity • Multi-Signal Corroboration Rule • Audit Case Files
              </p>
            </div>
          </div>

          {/* Quick Portfolio Stats */}
          <div className="flex items-center gap-3 text-xs font-mono">
            <div className="bg-slate-900/80 px-3 py-2 rounded-lg border border-slate-800 text-center">
              <div className="text-slate-400 text-[10px] uppercase">Portfolio</div>
              <div className="text-slate-100 font-bold">220 Merchants</div>
            </div>
            <div className="bg-slate-900/80 px-3 py-2 rounded-lg border border-slate-800 text-center">
              <div className="text-slate-400 text-[10px] uppercase">Transactions</div>
              <div className="text-slate-100 font-bold">1.03M UPI</div>
            </div>
            <div className="bg-blue-950/50 px-3 py-2 rounded-lg border border-blue-800/40 text-center">
              <div className="text-blue-300 text-[10px] uppercase font-sans font-semibold">Median Lead</div>
              <div className="text-blue-400 font-bold text-sm">{h.median_lead_days} Days</div>
            </div>
            <div className="bg-emerald-950/50 px-3 py-2 rounded-lg border border-emerald-800/40 text-center">
              <div className="text-emerald-300 text-[10px] uppercase font-sans font-semibold">Cost Avoided</div>
              <div className="text-emerald-400 font-bold text-sm">₹{(h.cost_avoided_inr / 10000000).toFixed(2)} Cr</div>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex space-x-1 mt-4 overflow-x-auto pb-1 border-t border-slate-800/80 pt-3">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-3.5 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                activeTab === t.id
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-900/40 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}
