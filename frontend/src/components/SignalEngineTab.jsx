import React, { useState } from 'react';
import { Sparkles, TrendingUp, Network, BarChart2, ShieldCheck, Check, AlertCircle, Info } from 'lucide-react';
import { evaluationData } from '../data/evaluationData';

export default function SignalEngineTab() {
  const [activeSignal, setActiveSignal] = useState('velocity');
  const thr = evaluationData.thresholds;

  const signals = [
    {
      id: 'velocity',
      name: 'S3: Peer-Relative Velocity',
      symbol: 'velocity_peer_z',
      family: 'velocity',
      threshold: `${thr.velocity_peer_z.toFixed(2)}σ`,
      thresholdType: 'Absolute Canonical Scale',
      description: 'Merchant\'s 7-day vs 35-day growth ratio, robust z-scored cross-sectionally against all merchants on the same day t.',
      keyStrength: 'Completely immune to portfolio-wide festival surges (Diwali). Only fires when a merchant accelerates against the contemporaneous portfolio baseline.',
      failureMode: 'A vertical-specific event (e.g. travel surge on long weekend) could temporarily elevate that vertical; mitigated by requiring 2-family corroboration.',
    },
    {
      id: 'content',
      name: 'S1: Descriptor Category Mismatch',
      symbol: 'category_mismatch',
      family: 'content',
      threshold: `${(thr.category_mismatch * 100).toFixed(1)}%`,
      thresholdType: 'Portfolio Quantile (p91)',
      description: 'Share of recent 14-day transactions whose free-text descriptor implies a category different from the merchant\'s declared KYC category, in excess of own baseline.',
      keyStrength: 'O(vocabulary) Gemini / fallback classification over 63 unique descriptors. Differenced against merchant\'s own 30-day baseline to accommodate broad catalogues.',
      failureMode: 'Legitimate category expansion/pivots produce false positives (e.g. restaurant launching grocery line); marked as legitimate confounders.',
    },
    {
      id: 'distribution',
      name: 'S2: Ticket Size Distribution PSI',
      symbol: 'ticket_psi',
      family: 'distribution',
      threshold: `${thr.ticket_psi.toFixed(2)}`,
      thresholdType: 'Absolute Canonical Scale (>0.25 significant shift)',
      description: 'Population Stability Index (PSI) of trailing 14-day ticket sizes compared to the merchant\'s own 30-day post-onboarding reference distribution, using fixed decile bins.',
      keyStrength: 'Catches ticket-splitting, high-ticket fraud migration, and product-mix mutations without relying on raw volume.',
      failureMode: 'Drifted merchant-days inflate distribution tails; using canonical 0.25 prevents quantile tail pollution.',
    },
    {
      id: 'network',
      name: 'S4: Network & Identifier Overlap',
      symbol: 'network_overlap',
      family: 'network',
      threshold: `${thr.network_overlap.toFixed(2)}`,
      thresholdType: 'Absolute Jaccard Floor (0.35 shared account)',
      description: 'Max Jaccard overlap of trailing 21-day payer-VPA population against any other portfolio merchant, floored at 0.35 for shared settlement accounts.',
      keyStrength: 'Direct structural link detection for undisclosed third-party layering on UPI rails. Recomputed on weekly rolling graph refresh.',
      failureMode: 'Legitimately related entities (franchises, sister brands) share payers; requires whitelist in production.',
    },
  ];

  return (
    <div className="space-y-8">
      {/* 4 Signal Family Cards */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-white">4 Independent Walk-Forward Signal Families</h3>
            <p className="text-xs text-slate-400 mt-0.5">Computed daily with strict no-peek discipline (only transactions with day &le; t)</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {signals.map((sig) => (
            <div
              key={sig.id}
              onClick={() => setActiveSignal(sig.id)}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${
                activeSignal === sig.id
                  ? 'bg-blue-950/40 border-blue-500 shadow-lg shadow-blue-950/50 ring-1 ring-blue-500/50'
                  : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {sig.family}
                </span>
                <span className="text-xs font-mono font-bold text-blue-400">{sig.threshold}</span>
              </div>
              <h4 className="text-sm font-bold text-white mb-1">{sig.name}</h4>
              <p className="text-xs text-slate-400 line-clamp-3 mt-1.5">{sig.description}</p>
              <div className="mt-3 pt-2 border-t border-slate-800/80 text-[10px] text-slate-500 font-mono">
                Scale: {sig.thresholdType}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Deep-Dive: Selected Signal Details */}
      {(() => {
        const cur = signals.find((s) => s.id === activeSignal);
        return (
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div>
                <span className="text-xs font-mono text-blue-400 font-semibold uppercase tracking-wider">
                  Deep-Dive: {cur.symbol}
                </span>
                <h3 className="text-lg font-bold text-white mt-0.5">{cur.name}</h3>
              </div>
              <div className="text-right font-mono">
                <span className="text-xs text-slate-400">Calibrated Bar: </span>
                <span className="text-sm font-bold text-blue-400">{cur.threshold}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
              <div className="space-y-4">
                <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                  <h4 className="font-semibold text-slate-200 mb-1.5 flex items-center gap-1.5">
                    <Check className="w-4 h-4 text-emerald-400" />
                    <span>Mathematical Construction & Strength</span>
                  </h4>
                  <p className="text-slate-300 leading-relaxed">{cur.keyStrength}</p>
                </div>
                <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                  <h4 className="font-semibold text-slate-200 mb-1.5 flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4 text-amber-400" />
                    <span>Known Failure Mode & Guardrail</span>
                  </h4>
                  <p className="text-slate-300 leading-relaxed">{cur.failureMode}</p>
                </div>
              </div>

              {/* Diwali Surge Interactive Visual Box */}
              <div className="bg-slate-950/80 border border-blue-900/40 p-5 rounded-xl flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-blue-300 uppercase tracking-wide">
                      Diwali Festival Surge (Days 96–116)
                    </span>
                    <span className="text-[10px] bg-blue-900/40 text-blue-300 px-2 py-0.5 rounded border border-blue-800 font-mono">
                      Defensibility Proof
                    </span>
                  </div>
                  <p className="text-slate-300 text-xs leading-relaxed mb-4">
                    During festival seasons (Diwali, Big Billion Days), every e-commerce & F&B merchant ramps by 1.7x–2.4x.
                  </p>

                  <div className="space-y-3 font-mono text-xs">
                    <div className="bg-rose-950/30 border border-rose-900/50 p-3 rounded-lg">
                      <div className="text-rose-400 font-semibold mb-1">Naive Absolute Velocity Detector:</div>
                      <div className="text-slate-300 text-[11px]">
                        Fires alerts on 100% of merchants during days 96–116 → Ops team overwhelms and shuts detector off within a week.
                      </div>
                    </div>

                    <div className="bg-emerald-950/30 border border-emerald-900/50 p-3 rounded-lg">
                      <div className="text-emerald-400 font-semibold mb-1">DriftWatch Peer-Relative Z-Score:</div>
                      <div className="text-slate-300 text-[11px]">
                        Cross-sectional median lifts together → z-score remains ≈ 0.0σ. Stays completely silent during Diwali across the entire book.
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
                  <span>Reads contemporaneous day t portfolio cross-section</span>
                  <span className="text-blue-400 font-semibold">No lookahead leak</span>
                </div>
              </div>
            </div>
          </div>
        );
      })()}

      {/* The Two-Branch Trigger Rule Structure */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <h3 className="text-base font-bold text-white mb-2">The Explicit Two-Branch Trigger Rule</h3>
        <p className="text-xs text-slate-400 mb-4">
          Deterministic quantitative rule that compliance analysts and scheme auditors can inspect and replay:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-slate-950/70 border border-blue-500/30 rounded-xl p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">Branch A • Corroboration</span>
              <span className="text-[10px] bg-blue-900/40 text-blue-300 px-2 py-0.5 rounded font-mono">Action: Escalate</span>
            </div>
            <div className="text-xs font-bold text-white mb-2 font-mono">
              &ge; 2 distinct signal FAMILIES cross threshold in rolling 14-day window
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Guarantees no single noisy feature (e.g. single-day ticket variance or viral product launch) opens a high-tier escalation on its own.
            </p>
          </div>

          <div className="bg-slate-950/70 border border-amber-500/30 rounded-xl p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">Branch B • Sustained Extreme</span>
              <span className="text-[10px] bg-amber-900/40 text-amber-300 px-2 py-0.5 rounded font-mono">Action: Investigate</span>
            </div>
            <div className="text-xs font-bold text-white mb-2 font-mono">
              1 family &ge; 2.5x threshold for &ge; 5 consecutive observation days
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Added because bust-outs cross velocity at z ≈ 5 and cross nothing else. Tiered with a higher bar, persistence requirement, and weaker recommended action.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
