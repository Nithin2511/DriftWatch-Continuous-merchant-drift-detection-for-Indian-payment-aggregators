import React, { useState } from 'react';
import { DollarSign, Scale, TrendingUp, AlertCircle, Info, Calculator, ShieldCheck } from 'lucide-react';
import { evaluationData } from '../data/evaluationData';

export default function EconomicsTab() {
  const h = evaluationData.held_out;
  const [costFp, setCostFp] = useState(12000);
  const [costMiss, setCostMiss] = useState(850000);

  const nDrifters = h.n_drifters;
  const nCaught = h.caught;
  const nMissed = nDrifters - nCaught;
  const nFp = h.n_false_positives;

  // Calculations
  const expCostDriftWatch = (nFp * costFp) + (nMissed * costMiss);
  const expCostDoNothing = nDrifters * costMiss;
  const netAvoided = expCostDoNothing - expCostDriftWatch;
  const breakEvenCostPerFp = nFp > 0 ? (nCaught * costMiss) / nFp : 0;

  const formatInr = (num) => {
    if (Math.abs(num) >= 10000000) return `₹${(num / 10000000).toFixed(2)} Cr`;
    if (Math.abs(num) >= 100000) return `₹${(num / 100000).toFixed(1)} Lakh`;
    return `₹${num.toLocaleString('en-IN')}`;
  };

  return (
    <div className="space-y-8">
      {/* Interactive Unit Economics Simulator */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Calculator className="w-5 h-5 text-blue-400" />
              <span>Interactive Break-Even & Unit Economics Simulator</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Test portfolio economic sensitivity against analyst review friction and scheme fine exposure.
            </p>
          </div>
          <span className="text-xs font-mono bg-blue-950/60 text-blue-300 px-3 py-1 rounded-lg border border-blue-800/40">
            Held-out book ({evaluationData.n_held_out} merchants)
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Sliders Left Column */}
          <div className="lg:col-span-6 space-y-6">
            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800">
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-semibold text-slate-300">
                  Cost per False Positive Review:
                </label>
                <span className="font-mono font-bold text-sm text-blue-400">{formatInr(costFp)}</span>
              </div>
              <input
                type="range"
                min="2000"
                max="50000"
                step="1000"
                value={costFp}
                onChange={(e) => setCostFp(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-1">
                <span>₹2,000 (quick check)</span>
                <span>₹12,000 (baseline)</span>
                <span>₹50,000 (high friction)</span>
              </div>
              <p className="text-[11px] text-slate-400 mt-2">
                Analyst investigation time + merchant outreach friction.
              </p>
            </div>

            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800">
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-semibold text-slate-300">
                  Cost per Missed Drift Exposure:
                </label>
                <span className="font-mono font-bold text-sm text-rose-400">{formatInr(costMiss)}</span>
              </div>
              <input
                type="range"
                min="200000"
                max="2000000"
                step="50000"
                value={costMiss}
                onChange={(e) => setCostMiss(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-rose-500"
              />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-1">
                <span>₹2.0L</span>
                <span>₹8.5L (scheme fine + loss)</span>
                <span>₹20.0L (catastrophic)</span>
              </div>
              <p className="text-[11px] text-slate-400 mt-2">
                Mastercard BRAM/SMMP fine + chargeback write-offs + regulatory remediation.
              </p>
            </div>
          </div>

          {/* Results Output Right Column */}
          <div className="lg:col-span-6 bg-slate-950/90 border border-slate-800 p-5 rounded-xl space-y-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
              Simulated Portfolio Economics
            </div>

            <div className="space-y-2.5 font-mono text-xs">
              <div className="flex justify-between p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/60">
                <span className="text-slate-400 font-sans">Cost with DriftWatch ({nFp} FPs + {nMissed} Missed):</span>
                <span className="font-bold text-slate-200">{formatInr(expCostDriftWatch)}</span>
              </div>
              <div className="flex justify-between p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/60">
                <span className="text-slate-400 font-sans">Cost Doing Nothing ({nDrifters} Drifters Missed):</span>
                <span className="font-bold text-rose-300">{formatInr(expCostDoNothing)}</span>
              </div>
              <div className="flex justify-between p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/40">
                <span className="text-emerald-300 font-sans font-bold">Net Financial Loss Avoided:</span>
                <span className="font-bold text-emerald-400 text-sm">{formatInr(netAvoided)}</span>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800/80 bg-blue-950/20 p-3 rounded-lg border border-blue-800/30">
              <div className="text-xs text-blue-300 font-sans font-semibold mb-1">
                The Decision Boundary: Break-Even Cost per FP
              </div>
              <div className="text-2xl font-bold font-mono text-blue-400">
                {formatInr(breakEvenCostPerFp)}
              </div>
              <p className="text-[11px] text-slate-300 mt-1">
                DriftWatch remains economically positive unless the operational cost to review a single false positive exceeds <strong className="text-white font-mono">{formatInr(breakEvenCostPerFp)}</strong>.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* The 5 Pillars of FP Scalability from docs/PANEL_QA.md */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <h3 className="text-base font-bold text-white mb-2">
          Answering the 10M-Merchant Scalability Question Honestly
        </h3>
        <p className="text-xs text-slate-400 mb-4">
          How to answer Razorpay panel engineers on why a ~10-12% FP rate is defensible and how to scale it:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            <span className="text-blue-400 font-bold font-mono block mb-1">1. Windowed Observation Rate</span>
            <p className="text-slate-300 text-[11px] leading-relaxed">
              The FP rate is measured over a 150-day window, not per day. 9 false positives across 71 clean merchants over 5 months equates to roughly <strong>1 false alarm per merchant every ~4 years</strong>.
            </p>
          </div>

          <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            <span className="text-blue-400 font-bold font-mono block mb-1">2. Controllable FP Budget</span>
            <p className="text-slate-300 text-[11px] leading-relaxed">
              <code className="text-blue-300 font-mono">max_fp_rate</code> is an explicit calibration constraint. Risk teams set it based on investigation capacity and calibrate the grid to that ceiling.
            </p>
          </div>

          <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            <span className="text-blue-400 font-bold font-mono block mb-1">3. Confounders are Useful Audits</span>
            <p className="text-slate-300 text-[11px] leading-relaxed">
              {h.n_fp_confounders} of {h.n_false_positives} false positives are legitimate category pivots. Under RBI rules, merchants operating in an outdated MCC require recoding anyway — these are necessary compliance re-alignments.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
