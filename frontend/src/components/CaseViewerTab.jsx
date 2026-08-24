import React, { useState } from 'react';
import { Search, Clock, FileText, AlertTriangle } from 'lucide-react';
import { casesData } from '../data/casesData';
import { evaluationData } from '../data/evaluationData';

export default function CaseViewerTab({ selectedCaseId, setSelectedCaseId }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all'); // all, tp, fp_conf, fp_plain

  // Case files are written for held-out triggers only, so held-out scoring is the only
  // ground truth that applies to them. Merging the development split's false positives in
  // here would classify a case against a split it was never scored on.
  const allFp = new Set(evaluationData.held_out.fp_ids);
  const allConf = new Set(evaluationData.held_out.fp_confounder_ids || []);

  // Enrich cases with classification
  const enrichedCases = casesData.map((c) => {
    const mid = c.subject_entity.merchant_id;
    let status = 'TRUE POSITIVE';
    let statusColor = 'emerald';
    if (allFp.has(mid)) {
      if (allConf.has(mid)) {
        status = 'FALSE POSITIVE (Legitimate Change)';
        statusColor = 'amber';
      } else {
        status = 'FALSE POSITIVE (Unexplained)';
        statusColor = 'rose';
      }
    }
    return { ...c, status, statusColor };
  });

  const filteredCases = enrichedCases.filter((c) => {
    const mid = c.subject_entity.merchant_id.toLowerCase();
    const caseId = c.case_id.toLowerCase();
    const cat = c.subject_entity.declared_category.toLowerCase();
    const branch = c.grounds_for_review.branch.toLowerCase();
    const matchesSearch = mid.includes(searchTerm.toLowerCase()) ||
                          caseId.includes(searchTerm.toLowerCase()) ||
                          cat.includes(searchTerm.toLowerCase()) ||
                          branch.includes(searchTerm.toLowerCase());

    if (!matchesSearch) return false;
    if (filterType === 'tp') return !allFp.has(c.subject_entity.merchant_id);
    if (filterType === 'fp_conf') return allConf.has(c.subject_entity.merchant_id);
    if (filterType === 'fp_plain') return allFp.has(c.subject_entity.merchant_id) && !allConf.has(c.subject_entity.merchant_id);
    return true;
  });

  const activeCase = filteredCases.find((c) => c.subject_entity.merchant_id === selectedCaseId) ||
                     filteredCases[0] ||
                     enrichedCases[0];

  return (
    <div className="space-y-6">
      {/* False Positive Demonstration Banner */}
      <div className="bg-amber-950/20 border border-amber-500/30 rounded-2xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-lg">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400 mt-0.5">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-amber-300 uppercase tracking-wide">
              Transparency in Production: Real False Positives Reported
            </h4>
            <p className="text-xs text-slate-300 mt-0.5">
              A demo with no false positives is a sales pitch. Inspect <strong className="text-amber-300 font-mono">DW-MID0093-D109</strong> (a travel agency that pivoted category) to see how the system generates structured dossiers even when wrong.
            </p>
          </div>
        </div>
        <button
          onClick={() => {
            setSelectedCaseId('MID0093');
            setFilterType('all');
            setSearchTerm('');
          }}
          className="px-3.5 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors"
        >
          View Confounder Case (MID0093) →
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
          <span className="text-slate-400 text-xs font-semibold mr-1">Filter:</span>
          {[
            { id: 'all', label: `All Cases (${enrichedCases.length})` },
            { id: 'tp', label: 'True Positives' },
            { id: 'fp_conf', label: 'Legitimate Pivots (Confounders)' },
            { id: 'fp_plain', label: 'Unexplained FP' },
          ].map((btn) => (
            <button
              key={btn.id}
              onClick={() => setFilterType(btn.id)}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                filterType === btn.id
                  ? 'bg-blue-600 text-white font-semibold shadow'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {btn.label}
            </button>
          ))}
        </div>

        <div className="relative w-full md:w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search MID, case, category..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
          />
        </div>
      </div>

      {/* Main 2-Column Split: Case List & Active Dossier */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Case List */}
        <div className="lg:col-span-4 bg-slate-900/80 border border-slate-800 rounded-2xl p-3 shadow-xl max-h-[780px] overflow-y-auto space-y-2">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-2 py-1">
            Generated Cases ({filteredCases.length})
          </div>

          {filteredCases.map((c) => {
            const isSelected = activeCase && activeCase.case_id === c.case_id;
            return (
              <div
                key={c.case_id}
                onClick={() => setSelectedCaseId(c.subject_entity.merchant_id)}
                className={`p-3 rounded-xl border cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-blue-950/60 border-blue-500 shadow-md ring-1 ring-blue-500/40'
                    : 'bg-slate-950/50 border-slate-800/80 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-mono font-bold text-xs text-white">{c.case_id}</span>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                    c.statusColor === 'emerald'
                      ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/60'
                      : c.statusColor === 'amber'
                      ? 'bg-amber-950/60 text-amber-300 border border-amber-800/60'
                      : 'bg-rose-950/60 text-rose-300 border border-rose-800/60'
                  }`}>
                    {c.status.includes('(') ? c.status.split('(')[1].replace(')', '') : 'True Positive'}
                  </span>
                </div>

                <div className="text-xs text-slate-300 flex items-center justify-between">
                  <span className="capitalize">{c.subject_entity.declared_category.replace(/_/g, ' ')}</span>
                  <span className="font-mono text-slate-400 text-[11px]">Day {c.trigger_day} ({c.days_since_onboarding}d post-KYC)</span>
                </div>

                <div className="mt-2 pt-1.5 border-t border-slate-800/60 text-[11px] text-slate-400 flex items-center justify-between font-mono">
                  <span>{c.grounds_for_review.branch.split('_')[0]} • {c.grounds_for_review.families_fired.join(', ')}</span>
                  <span className="text-blue-400">View Dossier →</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column: Full Audit Case Dossier */}
        {activeCase ? (
          <div className="lg:col-span-8 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-6">
            {/* Dossier Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold text-white font-mono">{activeCase.case_id}</h3>
                  <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${
                    activeCase.statusColor === 'emerald'
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : activeCase.statusColor === 'amber'
                      ? 'bg-amber-950 text-amber-300 border border-amber-800'
                      : 'bg-rose-950 text-rose-300 border border-rose-800'
                  }`}>
                    [{activeCase.status}]
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1 font-mono">
                  Generated at UTC: {activeCase.generated_at_utc} • Trigger Day: {activeCase.trigger_day} ({activeCase.days_since_onboarding} days after KYC)
                </p>
              </div>

              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl px-3 py-2 text-right">
                <div className="text-[10px] text-amber-400 font-semibold uppercase tracking-wider flex items-center gap-1 justify-end">
                  <Clock className="w-3 h-3" />
                  <span>Disposition Due</span>
                </div>
                <div className="text-xs font-bold text-white mt-0.5">Within 72 Hours</div>
                <div className="text-[10px] text-slate-400 font-mono">Mastercard SMMP</div>
              </div>
            </div>

            {/* Subject Entity & Grounds Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800">
                <h4 className="font-semibold text-slate-300 uppercase tracking-wider text-[11px] mb-2.5">
                  1. Subject Entity (Declared KYC Profile)
                </h4>
                <div className="space-y-1.5 font-mono text-slate-300">
                  <div className="flex justify-between"><span className="text-slate-400">Merchant ID:</span> <span className="font-bold text-white">{activeCase.subject_entity.merchant_id}</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">Declared Category:</span> <span className="text-blue-300">{activeCase.subject_entity.declared_category}</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">Declared Avg Ticket:</span> <span>₹{activeCase.subject_entity.declared_avg_ticket_inr}</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">Declared Monthly Vol:</span> <span>{activeCase.subject_entity.declared_monthly_volume} txns</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">Settlement Acc:</span> <span className="text-slate-400">{activeCase.subject_entity.settlement_account}</span></div>
                </div>
              </div>

              <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800">
                <h4 className="font-semibold text-slate-300 uppercase tracking-wider text-[11px] mb-2.5">
                  2. Grounds for Review (Trigger Rule)
                </h4>
                <div className="space-y-2">
                  <div className="font-mono text-blue-300 font-semibold text-xs">
                    {activeCase.grounds_for_review.branch}
                  </div>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    {activeCase.grounds_for_review.rule}
                  </p>
                  <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400 font-mono">
                    Fired Families: <strong className="text-white">{activeCase.grounds_for_review.families_fired.join(', ')}</strong>
                  </div>
                </div>
              </div>
            </div>

            {/* Fired Signal Evidence Table */}
            <div>
              <h4 className="font-semibold text-slate-300 uppercase tracking-wider text-xs mb-2">
                3. Quantitative Signal Evidence (No Lookahead)
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs bg-slate-950/70 border border-slate-800 rounded-xl">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-mono text-[11px]">
                      <th className="p-3 font-semibold">Signal</th>
                      <th className="p-3 font-semibold text-center">Family</th>
                      <th className="p-3 font-semibold text-right">At Cross</th>
                      <th className="p-3 font-semibold text-right">Threshold</th>
                      <th className="p-3 font-semibold text-center">Crossed Day</th>
                      <th className="p-3 font-semibold text-right">At Trigger Day</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {activeCase.signals_fired.map((s, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/40">
                        <td className="p-3 font-bold text-white font-sans">{s.signal}</td>
                        <td className="p-3 text-center text-slate-400 capitalize">{s.family}</td>
                        <td className="p-3 text-right font-bold text-blue-400">{s.value.toFixed(3)}</td>
                        <td className="p-3 text-right text-slate-400">{s.threshold.toFixed(3)}</td>
                        <td className="p-3 text-center text-slate-300">Day {s.first_crossed_day}</td>
                        <td className="p-3 text-right text-slate-300">
                          {s.value_at_trigger_day !== undefined ? s.value_at_trigger_day.toFixed(3) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-[11px] text-slate-400 mt-1.5">
                * Both reading at qualifying cross and at trigger day are logged so reviewers inspect decay rather than only peak readings.
              </p>
            </div>

            {/* Supporting Behavioural Deltas */}
            {activeCase.supporting_data && (
              <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800 text-xs">
                <h4 className="font-semibold text-slate-300 uppercase tracking-wider text-[11px] mb-3">
                  4. Supporting Shift Metrics (14-Day Trailing Window)
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono mb-3">
                  <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">
                    <div className="text-slate-400 text-[10px]">Median Ticket Shift</div>
                    <div className="text-slate-100 font-bold mt-0.5">
                      ₹{activeCase.supporting_data.baseline_median_ticket_inr} → ₹{activeCase.supporting_data.current_median_ticket_inr}
                    </div>
                    <div className="text-blue-400 text-[10px]">({activeCase.supporting_data.ticket_shift_multiple}x)</div>
                  </div>
                  <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">
                    <div className="text-slate-400 text-[10px]">Daily Volume Shift</div>
                    <div className="text-slate-100 font-bold mt-0.5">
                      {activeCase.supporting_data.baseline_daily_txns} → {activeCase.supporting_data.current_daily_txns} txn/d
                    </div>
                    <div className="text-blue-400 text-[10px]">({activeCase.supporting_data.volume_shift_multiple}x)</div>
                  </div>
                  <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">
                    <div className="text-slate-400 text-[10px]">Distinct Payers</div>
                    <div className="text-slate-100 font-bold mt-0.5">
                      {activeCase.supporting_data.distinct_payer_vpas_in_window} VPAs
                    </div>
                    <div className="text-slate-400 text-[10px]">in 14d window</div>
                  </div>
                  <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">
                    <div className="text-slate-400 text-[10px]">Linked Merchant</div>
                    <div className="text-slate-100 font-bold mt-0.5">
                      {activeCase.network_context.linked_merchant || 'None'}
                    </div>
                    <div className="text-slate-400 text-[10px]">Shared Acc: {String(activeCase.network_context.shared_settlement_account)}</div>
                  </div>
                </div>

                {activeCase.supporting_data.current_top_descriptors && (
                  <div className="text-[11px] text-slate-300 font-mono pt-2 border-t border-slate-800">
                    <span className="text-slate-400 font-sans">Observed Descriptors: </span>
                    {activeCase.supporting_data.current_top_descriptors.map((d, i) => (
                      <span key={i} className="inline-block bg-slate-900 px-2 py-0.5 rounded mr-1.5 mb-1 text-slate-200 border border-slate-800">
                        {d.descriptor} <strong className="text-blue-400">({d.n})</strong>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Recommended Action & LLM Narrative */}
            <div className="space-y-4">
              <div className="bg-blue-950/30 border border-blue-800/40 p-4 rounded-xl text-xs">
                <div className="text-[11px] font-semibold text-blue-300 uppercase tracking-wider mb-1">
                  5. Recommended Compliance Disposition (Directions Phrasing)
                </div>
                <p className="text-white font-medium leading-relaxed font-mono text-xs">
                  {activeCase.recommended_action}
                </p>
              </div>

              <div className="bg-slate-950/80 border border-slate-800 p-4 rounded-xl text-xs">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-semibold text-purple-300 uppercase tracking-wider flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-purple-400" />
                    <span>6. AI Compliance Case Narrative</span>
                  </span>
                  <span className="text-[10px] font-mono bg-slate-900 text-slate-400 px-2 py-0.5 rounded border border-slate-800">
                    Provenance: {activeCase.provenance?.narrative_mode || 'template'}
                  </span>
                </div>
                <div className="text-slate-200 leading-relaxed whitespace-pre-line text-xs font-sans">
                  {activeCase.narrative}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
