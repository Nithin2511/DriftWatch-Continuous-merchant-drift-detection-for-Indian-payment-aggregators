import React from 'react';
import { AlertTriangle, Users, Flame, ShieldAlert, CheckCircle2, ChevronRight, BarChart3, HelpCircle } from 'lucide-react';
import { evaluationData } from '../data/evaluationData';

export default function ThreatModelsTab({ setActiveTab, setSelectedCaseId }) {
  const byType = evaluationData.held_out_by_type;

  const threatDetails = [
    {
      id: 'third_party_layering',
      title: 'Third-Party Processing Layering',
      subtitle: 'Undisclosed merchant processing transactions on behalf of another entity',
      stats: byType.third_party_layering,
      leadTime: '43.0 Days',
      color: 'blue',
      border: 'border-blue-500/40',
      bg: 'bg-blue-950/20',
      tag: '100% Catch Rate',
      signalsUsed: 'Payer-VPA Jaccard Overlap + Shared Settlement Account + Category Mismatch',
      howItDrifts: 'Payer VPAs begin drawing from a principal merchant\'s customer pool (up to 60%), ticket sizes converge toward principal, 50% route settlements to principal account.',
      whyItsHard: 'Half of layering cases do NOT share a settlement account, so network links alone cannot catch the entire class without descriptor & ticket corroboration.',
      keyCase: 'MID0153',
    },
    {
      id: 'prohibited_category',
      title: 'Prohibited Category Migration',
      subtitle: 'Gradual migration into restricted goods (nutraceuticals, replica, gaming topups)',
      stats: byType.prohibited_category,
      leadTime: '28.0 Days',
      color: 'emerald',
      border: 'border-emerald-500/40',
      bg: 'bg-emerald-950/20',
      tag: '80% Catch Rate',
      signalsUsed: 'Descriptor Category Mismatch (Gemini / Lexicon) + Ticket Distribution PSI',
      howItDrifts: 'Descriptor mix migrates toward restricted items (up to 55% over 30 days), ticket sizes shift +0.35 log, volume increases by only +25%.',
      whyItsHard: 'Volume ratio median is 1.12x — sits completely inside normal organic growth noise (non-drifters reach 1.21x at p90). Single-variable volume detectors cannot separate it.',
      keyCase: 'MID0138',
    },
    {
      id: 'bust_out',
      title: 'Merchant Bust-Out & Sudden Ramp',
      subtitle: 'Rapid volume acceleration followed by merchant abandonment and refund spikes',
      stats: byType.bust_out,
      leadTime: '19.0 Days',
      color: 'amber',
      border: 'border-amber-500/40',
      bg: 'bg-amber-950/20',
      tag: '60% Catch Rate (Branch B)',
      signalsUsed: 'Velocity Peer-Z Extreme (Branch B: >= 2.5x threshold for >= 5 consecutive days)',
      howItDrifts: '21-day volume ramp up to ~4.4x with ticket inflation, followed by a sudden collapse and 5-20% refund rate spike.',
      whyItsHard: 'Structurally single-family: bust-outs cross velocity at z ≈ 5 and cross NOTHING else. A pure 2-family rule catches 0/7. Fixed via tiered Branch B.',
      keyCase: 'MID0105',
    },
  ];

  return (
    <div className="space-y-8">
      {/* 3 Threat Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {threatDetails.map((threat) => (
          <div
            key={threat.id}
            className={`bg-slate-900/90 border ${threat.border} rounded-2xl p-6 shadow-xl flex flex-col justify-between relative overflow-hidden`}
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 rounded-full blur-2xl pointer-events-none" />

            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-mono uppercase tracking-wider px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                  Threat Model
                </span>
                <span className="text-xs font-bold text-blue-400 bg-blue-950/60 px-2.5 py-0.5 rounded-full border border-blue-800/50">
                  {threat.tag}
                </span>
              </div>

              <h3 className="text-base font-bold text-white mb-1">{threat.title}</h3>
              <p className="text-xs text-slate-400 mb-4">{threat.subtitle}</p>

              <div className="bg-slate-950/70 rounded-xl p-3.5 border border-slate-800 mb-4">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="text-slate-400">Held-Out Catch:</span>
                  <span className="font-mono font-bold text-emerald-400">{threat.stats.caught} / {threat.stats.n} merchants</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Median Warning Bought:</span>
                  <span className="font-mono font-bold text-blue-400 text-sm">{threat.leadTime}</span>
                </div>
              </div>

              <div className="space-y-2.5 text-xs text-slate-300">
                <div>
                  <span className="text-slate-400 font-semibold block text-[11px] uppercase tracking-wide">Key Signals</span>
                  <span className="font-mono text-blue-300 text-[11px]">{threat.signalsUsed}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-semibold block text-[11px] uppercase tracking-wide">Drift Mechanism</span>
                  <p className="text-slate-300 text-[11px] leading-relaxed mt-0.5">{threat.howItDrifts}</p>
                </div>
                <div>
                  <span className="text-slate-400 font-semibold block text-[11px] uppercase tracking-wide">Why It Defeats Naive Detectors</span>
                  <p className="text-slate-300 text-[11px] leading-relaxed mt-0.5">{threat.whyItsHard}</p>
                </div>
              </div>
            </div>

            <div className="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between">
              <span className="text-[11px] text-slate-500 font-mono">Example: {threat.keyCase}</span>
              <button
                onClick={() => {
                  setSelectedCaseId(threat.keyCase);
                  setActiveTab('cases');
                }}
                className="text-xs font-semibold text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors"
              >
                Inspect Case File <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Pre-Registered Separability Proof Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>The Pre-Registered Separability Proof</span>
              <span className="text-xs bg-blue-950 text-blue-300 px-2 py-0.5 rounded border border-blue-800">
                docs/DATA_PLAN.md
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              14-day volume ratio around T0 — computed <em>before</em> any detector was built to guarantee the synthetic evaluation is genuinely adversarial.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-mono">
                <th className="pb-3 font-semibold">Cohort</th>
                <th className="pb-3 font-semibold text-center">p25 Volume Ratio</th>
                <th className="pb-3 font-semibold text-center text-blue-400">p50 (Median)</th>
                <th className="pb-3 font-semibold text-center">p75 Volume Ratio</th>
                <th className="pb-3 font-semibold">Evidentiary Implication for Aggregators</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              <tr className="bg-amber-950/10">
                <td className="py-3 font-sans font-medium text-amber-300">bust_out</td>
                <td className="py-3 text-center text-slate-300">1.84x</td>
                <td className="py-3 text-center font-bold text-amber-400">1.98x</td>
                <td className="py-3 text-center text-slate-300">2.12x</td>
                <td className="py-3 font-sans text-slate-300 text-[11px]">Clear volume ramp; caught via Branch B single-family sustained extreme</td>
              </tr>
              <tr className="bg-blue-950/10">
                <td className="py-3 font-sans font-medium text-blue-300">third_party_layering</td>
                <td className="py-3 text-center text-slate-300">1.17x</td>
                <td className="py-3 text-center font-bold text-blue-400">1.35x</td>
                <td className="py-3 text-center text-slate-300">1.44x</td>
                <td className="py-3 font-sans text-slate-300 text-[11px]">Moderate volume lift; caught via Payer-VPA population overlap + category change</td>
              </tr>
              <tr className="bg-emerald-950/20 border-y-2 border-emerald-500/40">
                <td className="py-3 font-sans font-bold text-emerald-300">prohibited_category</td>
                <td className="py-3 text-center text-slate-300">1.00x</td>
                <td className="py-3 text-center font-extrabold text-emerald-400 text-sm">1.12x</td>
                <td className="py-3 text-center text-slate-300">1.26x</td>
                <td className="py-3 font-sans font-semibold text-emerald-200 text-[11px]">
                  ★ Sits INSIDE non-drifter noise (p90 1.21x). Proves volume alone cannot catch it.
                </td>
              </tr>
              <tr>
                <td className="py-3 font-sans font-medium text-slate-400">non-drifters (organic)</td>
                <td className="py-3 text-center text-slate-500">—</td>
                <td className="py-3 text-center font-bold text-slate-300">1.02x</td>
                <td className="py-3 text-center text-slate-400">1.13x (p90 = 1.21x, max 1.64x)</td>
                <td className="py-3 font-sans text-slate-400 text-[11px]">Includes organic growth, weekday cycles, and Diwali festival surge</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
