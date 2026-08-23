import React, { useState } from 'react';
import Header from './components/Header';
import ClocksBanner from './components/ClocksBanner';
import OverviewTab from './components/OverviewTab';
import ThreatModelsTab from './components/ThreatModelsTab';
import SignalEngineTab from './components/SignalEngineTab';
import CaseViewerTab from './components/CaseViewerTab';
import EconomicsTab from './components/EconomicsTab';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedCaseId, setSelectedCaseId] = useState('MID0138');

  return (
    <div className="min-h-screen bg-[#070c18] text-slate-100 flex flex-col font-['Plus_Jakarta_Sans',sans-serif]">
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        <ClocksBanner />

        {activeTab === 'overview' && (
          <OverviewTab
            setActiveTab={setActiveTab}
            setSelectedCaseId={setSelectedCaseId}
          />
        )}
        {activeTab === 'threats' && (
          <ThreatModelsTab
            setActiveTab={setActiveTab}
            setSelectedCaseId={setSelectedCaseId}
          />
        )}
        {activeTab === 'signals' && (
          <SignalEngineTab />
        )}
        {activeTab === 'cases' && (
          <CaseViewerTab
            selectedCaseId={selectedCaseId}
            setSelectedCaseId={setSelectedCaseId}
          />
        )}
        {activeTab === 'economics' && (
          <EconomicsTab />
        )}
      </main>

      <footer className="border-t border-slate-800/80 bg-[#080e1e] py-6 px-6 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-200">DriftWatch</span>
            <span>•</span>
            <span>Razorpay AI Buildathon Submission (Track 02: AI Risk Manager)</span>
          </div>
          <div className="font-mono text-slate-500">
            Strict Defense-Only • UPI Native • Walk-Forward Lead-Time Evaluated
          </div>
        </div>
      </footer>
    </div>
  );
}
