import React from 'react';
import { ShieldCheck, Activity, AlertTriangle, FileText, CheckCircle2, DollarSign, Database, Cpu, GitBranch, Scale, Lock } from 'lucide-react';
import { evaluationData } from '../data/evaluationData';

export default function OverviewTab({ setActiveTab, setSelectedCaseId }) {
  const h = evaluationData.held_out;
  const d = evaluationData.development;

  return (
    <div className="space-y-8">
      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Median Lead Time Bought</span>
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-white">
            {h.median_lead_days.toFixed(1)} <span className="text-sm font-normal text-slate-400">days</span>
          </div>
          <div className="mt-2 text-xs text-slate-400 font-mono">
            IQR {h.p25_lead_days.toFixed(0)}–{h.p75_lead_days.toFixed(0)}d • Range {h.min_lead_days}–{h.max_lead_days}d
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Held-Out Catch Rate</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-emerald-400">
            {(h.catch_rate * 100).toFixed(1)}%
          </div>
          <div className="mt-2 text-xs text-slate-400 font-mono">
            {h.caught} of {h.n_drifters} caught before T_lag
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">False-Positive Rate</span>
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-amber-400">
            {(h.false_positive_rate * 100).toFixed(1)}%
          </div>
          <div className="mt-2 text-xs text-slate-400">
            {h.n_fp_confounders} legitimate pivots, {h.n_fp_plain} unexplained
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Net Cost Avoided</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-indigo-400">
            ₹{(h.cost_avoided_inr / 100000).toFixed(1)}L
          </div>
          <div className="mt-2 text-xs text-slate-400 font-mono">
            Break-even: ₹{(h.break_even_cost_per_fp_inr / 100000).toFixed(1)}L / FP
          </div>
        </div>
      </div>

      {/* Generalisation Gap & By-Type Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Generalisation Table */}
        <div className="lg:col-span-7 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>The Generalisation Gap — Reported Honestly</span>
                <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
                  60% Dev / 40% Held-Out
                </span>
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Full signal set, false-positive budget on the point estimate — the system's
                headline configuration. The no-content ablation and the upper-bound-budget
                sensitivity analysis are in docs/EVALUATION.md and are not shown here.
                Thresholds calibrated on development split only. Held-out split touched exactly once.
                With {h.n_drifters} held-out drifters every rate here carries a ±20-point 95% interval.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="pb-3 font-semibold">Evaluation Metric</th>
                  <th className="pb-3 font-semibold text-center">Development (132)</th>
                  <th className="pb-3 font-semibold text-center text-blue-400 font-mono">Held-Out (88)</th>
                  <th className="pb-3 font-semibold text-right">Generalisation Note</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                <tr>
                  <td className="py-3 font-sans font-medium text-slate-200">Catch Rate</td>
                  <td className="py-3 text-center text-slate-300">{(d.catch_rate * 100).toFixed(1)}% ({d.caught}/{d.n_drifters})</td>
                  <td className="py-3 text-center font-bold text-emerald-400">{(h.catch_rate * 100).toFixed(1)}% ({h.caught}/{h.n_drifters})</td>
                  <td className="py-3 text-right font-sans text-slate-400 text-[11px]">Held-out is higher, but n={h.n_drifters}: z=0.89, not significant</td>
                </tr>
                <tr>
                  <td className="py-3 font-sans font-medium text-slate-200">Median Lead Time</td>
                  <td className="py-3 text-center text-slate-300">{d.median_lead_days.toFixed(1)} days</td>
                  <td className="py-3 text-center font-bold text-blue-400">{h.median_lead_days.toFixed(1)} days</td>
                  <td className="py-3 text-right font-sans text-slate-400 text-[11px]">Stable signal magnitude property</td>
                </tr>
                <tr>
                  <td className="py-3 font-sans font-medium text-slate-200">False-Positive Rate</td>
                  <td className="py-3 text-center text-slate-300">{(d.false_positive_rate * 100).toFixed(1)}% ({d.n_false_positives})</td>
                  <td className="py-3 text-center font-bold text-amber-400">{(h.false_positive_rate * 100).toFixed(1)}% ({h.n_false_positives})</td>
                  <td className="py-3 text-right font-sans text-slate-400 text-[11px]">{h.n_fp_confounders}/{h.n_false_positives} legitimate pivots &middot; over the 10% dev budget</td>
                </tr>
                <tr>
                  <td className="py-3 font-sans font-medium text-slate-200">Break-Even FP Cost</td>
                  <td className="py-3 text-center text-slate-300">₹{(d.break_even_cost_per_fp_inr / 100000).toFixed(1)}L</td>
                  <td className="py-3 text-center font-bold text-indigo-400">₹{(h.break_even_cost_per_fp_inr / 100000).toFixed(1)}L</td>
                  <td className="py-3 text-right font-sans text-slate-400 text-[11px]">~110x the assumed ₹12k review cost</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Breakdown by Threat Model */}
        <div className="lg:col-span-5 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-white mb-1">Held-Out Threat Breakdown</h3>
            <p className="text-xs text-slate-400 mb-4">Stratified held-out performance across all 3 drift classes:</p>

            <div className="space-y-3">
              {Object.entries(evaluationData.held_out_by_type).map(([key, val]) => (
                <div key={key} className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-mono font-semibold text-slate-200 capitalize">
                      {key.replace(/_/g, ' ')}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Caught {val.caught} of {val.n} drifters ({(val.caught / val.n * 100).toFixed(0)}%)
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-bold text-blue-400 font-mono">
                      {val.median_lead ? `${val.median_lead.toFixed(0)}d lead` : '—'}
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono">median warning</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => setActiveTab('threats')}
            className="mt-4 w-full py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 rounded-xl text-xs font-semibold transition-colors"
          >
            Explore Threat Models & Separability Proof →
          </button>
        </div>
      </div>

      {/* 5-Component Architecture Diagram */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <h3 className="text-base font-bold text-white mb-2">5-Component Production Architecture</h3>
        <p className="text-xs text-slate-400 mb-6">
          Strict evidentiary separation: ML lives inside signals; trigger combination is a deterministic rule; Gemini synthesises case narratives.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <div className="bg-slate-950/80 border border-slate-800 p-4 rounded-xl relative group hover:border-blue-500/40 transition-colors">
            <div className="w-7 h-7 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 mb-3">
              <Database className="w-4 h-4" />
            </div>
            <div className="text-xs font-bold text-white">1. Data Layer</div>
            <div className="text-[11px] font-mono text-slate-400 mt-1">generate.py</div>
            <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
              220 merchants, 1.03M UPI txns. Ground truth (T0, T_lag) held back.
            </p>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-4 rounded-xl relative group hover:border-blue-500/40 transition-colors">
            <div className="w-7 h-7 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-3">
              <Cpu className="w-4 h-4" />
            </div>
            <div className="text-xs font-bold text-white">2. Signal Engine</div>
            <div className="text-[11px] font-mono text-slate-400 mt-1">signals.py</div>
            <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
              4 walk-forward signals: Content, Distribution (PSI), Velocity (z-score), Network.
            </p>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-4 rounded-xl relative group hover:border-blue-500/40 transition-colors">
            <div className="w-7 h-7 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400 mb-3">
              <GitBranch className="w-4 h-4" />
            </div>
            <div className="text-xs font-bold text-white">3. Trigger Layer</div>
            <div className="text-[11px] font-mono text-slate-400 mt-1">trigger.py</div>
            <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
              Branch A (Corroboration) & Branch B (Sustained Extreme). No black box.
            </p>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-4 rounded-xl relative group hover:border-blue-500/40 transition-colors">
            <div className="w-7 h-7 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 mb-3">
              <FileText className="w-4 h-4" />
            </div>
            <div className="text-xs font-bold text-white">4. Case File AI</div>
            <div className="text-[11px] font-mono text-slate-400 mt-1">casefile.py</div>
            <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
              Structured JSON dossier with a generated compliance narrative.
            </p>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-4 rounded-xl relative group hover:border-blue-500/40 transition-colors">
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 mb-3">
              <Scale className="w-4 h-4" />
            </div>
            <div className="text-xs font-bold text-white">5. Evaluation</div>
            <div className="text-[11px] font-mono text-slate-400 mt-1">evaluate.py</div>
            <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
              Lead time bought ($T_{'{lag}'} - T_{'{detect}'}$). Dev/held-out split discipline.
            </p>
          </div>
        </div>
      </div>

      {/* 4 Non-Negotiable Decisions */}
      <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
          <Lock className="w-3.5 h-3.5 text-blue-400" />
          <span>Core Design Decisions That Survive Engineering Interrogation</span>
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/60">
            <strong className="text-blue-300 font-semibold block mb-1">1. Peer-Relative Velocity (velocity_peer_z)</strong>
            <p className="text-slate-300 leading-relaxed">
              Z-scored cross-sectionally against portfolio on the same day. Diwali festival surges raise everyone equally, so portfolio is silent. Rogue acceleration against a flat book fires.
            </p>
          </div>
          <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/60">
            <strong className="text-blue-300 font-semibold block mb-1">2. Quantitative Rule, Not a Learned Combiner</strong>
            <p className="text-slate-300 leading-relaxed">
              A learned black-box combiner is undefensible in an RBI/scheme audit. ML stays inside individual signals; combination is an explicit 2-branch corroboration rule.
            </p>
          </div>
          <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/60">
            <strong className="text-blue-300 font-semibold block mb-1">3. The LLM Synthesises, Never Judges</strong>
            <p className="text-slate-300 leading-relaxed">
              Gemini classifies text descriptors (O(vocabulary), 63 calls) and writes case prose. It is NEVER asked "is this merchant fraudulent". Fire decision is 100% quantitative.
            </p>
          </div>
          <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/60">
            <strong className="text-blue-300 font-semibold block mb-1">4. The Output is a Case File, Not a Score</strong>
            <p className="text-slate-300 leading-relaxed">
              Mastercard SMMP requires proving when the trigger occurred, what was reviewed, and the basis for action within 72h. A single risk score cannot meet this duty.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
