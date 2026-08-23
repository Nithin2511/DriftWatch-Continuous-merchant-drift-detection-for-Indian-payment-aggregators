import React from 'react';
import { Clock, AlertOctagon, ArrowRight, Zap, ShieldCheck } from 'lucide-react';
import { evaluationData } from '../data/evaluationData';

export default function ClocksBanner() {
  // Read from the generated evaluation export, never hardcode. This banner is on every
  // tab, so a stale literal here would contradict every other number on the page.
  const h = evaluationData.held_out;
  const d = evaluationData.development;

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 mb-8">
      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            The problem
          </span>
        </div>

        <h2 className="text-lg md:text-xl font-bold text-white mb-4">
          The Two Mismatched Clocks: Regulatory Urgency vs Evidence Latency
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-stretch">
          {/* Clock 1: Regulatory */}
          <div className="bg-slate-950/70 border border-amber-500/30 rounded-xl p-4 flex flex-col justify-between relative group hover:border-amber-500/60 transition-colors">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">Clock 1 • Regulatory Duty</span>
                <Clock className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-3xl font-extrabold text-white mb-1">
                72 <span className="text-lg font-medium text-amber-400">Hours</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                <strong>Mastercard SMMP</strong> (live 24 Jul 2026) & <strong>RBI PA Directions 2025</strong> require immediate investigation or settlement block once warning signals appear.
              </p>
            </div>
            <div className="mt-3 pt-3 border-t border-slate-800/80 text-[11px] text-amber-300/90 font-mono">
              Requires immediate action
            </div>
          </div>

          {/* Center Bridge: DriftWatch */}
          <div className="bg-blue-950/30 border border-blue-500/40 rounded-xl p-4 flex flex-col justify-between relative">
            <div className="absolute top-2 right-2">
              <span className="bg-blue-500/15 text-blue-300 text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider border border-blue-500/30">
                DriftWatch
              </span>
            </div>
            <div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-300 mb-2 uppercase tracking-wider">
                <Zap className="w-4 h-4 text-blue-400" />
                <span>Headline Metric</span>
              </div>
              <div className="text-3xl font-extrabold text-blue-400 mb-1">
                {h.median_lead_days} <span className="text-lg font-medium text-blue-200">Days</span>
              </div>
              <p className="text-xs text-slate-200 leading-relaxed">
                <strong>Median Lead Time Bought</strong> on held-out split (IQR {h.p25_lead_days.toFixed(0)}–{h.p75_lead_days.toFixed(0)}d). Fires on continuous behavioural divergence <em>before</em> chargebacks begin.
              </p>
            </div>
            <div className="mt-3 pt-3 border-t border-blue-800/50 text-[11px] text-blue-300 font-mono flex items-center justify-between">
              <span>Catch Rate: <strong>{(h.catch_rate * 100).toFixed(1)}%</strong></span>
              <span>Dev: <strong>{d.median_lead_days}d</strong></span>
            </div>
          </div>

          {/* Clock 2: Lagging Evidence */}
          <div className="bg-slate-950/70 border border-rose-500/30 rounded-xl p-4 flex flex-col justify-between relative group hover:border-rose-500/60 transition-colors">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider">Clock 2 • Reality (Lagging)</span>
                <AlertOctagon className="w-4 h-4 text-rose-400" />
              </div>
              <div className="text-3xl font-extrabold text-white mb-1">
                30–90 <span className="text-lg font-medium text-rose-400">Days</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Time until confirming evidence arrives (chargeback surges, LEA settlement holds via CFCFRMS). Waiting for chargebacks leaves aggregators exposed to scheme fines.
              </p>
            </div>
            <div className="mt-3 pt-3 border-t border-slate-800/80 text-[11px] text-rose-300/90 font-mono">
              Too late for 72h SMMP clock
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
