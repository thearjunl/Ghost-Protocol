"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, ShieldOff, Loader2 } from "lucide-react";
import RiskBadge from "./RiskBadge";
import PolicyModal from "./PolicyModal";
import { toast } from "./Toast";
import type { Identity, AnalysisResult } from "@/lib/api";
import { analyzeIdentity, quarantineIdentity } from "@/lib/api";

interface Props {
  identities: Identity[];
  onRefresh: () => void;
}

const rowVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.04 },
  }),
  exit: { opacity: 0, x: -20 },
};

export default function IdentityTable({ identities, onRefresh }: Props) {
  const [filter, setFilter] = useState<"all" | "critical" | "warning" | "safe">(
    "all",
  );
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedIdentity, setSelectedIdentity] = useState<Identity | null>(
    null,
  );
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [quarantining, setQuarantining] = useState<string | null>(null);

  const filtered = identities.filter((id) => {
    if (filter === "critical") return id.risk_score > 80;
    if (filter === "warning") return id.risk_score > 50 && id.risk_score <= 80;
    if (filter === "safe") return id.risk_score <= 50;
    return true;
  });

  const handleViewRecommendation = useCallback(async (identity: Identity) => {
    setSelectedIdentity(identity);
    setAnalysis(null);
    setModalOpen(true);
    setAnalysisLoading(true);
    try {
      const result = await analyzeIdentity(identity.arn);
      setAnalysis(result);
    } catch (err) {
      toast("error", "AI analysis failed — is Ollama running?");
    } finally {
      setAnalysisLoading(false);
    }
  }, []);

  const handleQuarantine = useCallback(
    async (arn: string) => {
      if (!confirm("Are you sure you want to quarantine this identity? This will deny ALL permissions.")) return;
      setQuarantining(arn);
      try {
        await quarantineIdentity(arn);
        toast("success", "Identity quarantined successfully");
        onRefresh();
      } catch (err) {
        toast("error", "Quarantine failed — check permissions");
      } finally {
        setQuarantining(null);
      }
    },
    [onRefresh],
  );

  const filterButtons: { label: string; value: typeof filter }[] = [
    { label: "All", value: "all" },
    { label: "Critical", value: "critical" },
    { label: "Warning", value: "warning" },
    { label: "Safe", value: "safe" },
  ];

  return (
    <>
      {/* Filter bar */}
      <div className="mb-4 flex gap-2">
        {filterButtons.map((btn) => (
          <button
            key={btn.value}
            onClick={() => setFilter(btn.value)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              filter === btn.value
                ? "bg-ghost-600 text-white"
                : "bg-surface-200 text-gray-400 hover:bg-surface-300 hover:text-white"
            }`}
          >
            {btn.label}
          </button>
        ))}
        <span className="ml-auto text-xs text-gray-600">
          {filtered.length} identit{filtered.length === 1 ? "y" : "ies"}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-surface-300 bg-surface-100">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-surface-300 text-xs uppercase tracking-wider text-gray-500">
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Last Activity</th>
              <th className="px-4 py-3 text-center">Risk Score</th>
              <th className="px-4 py-3 text-center">Status</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence mode="popLayout">
              {filtered.map((identity, i) => (
                <motion.tr
                  key={identity.arn}
                  custom={i}
                  variants={rowVariants}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                  layout
                  className="border-b border-surface-300/50 transition-colors hover:bg-surface-200/50"
                >
                  <td className="max-w-[200px] truncate px-4 py-3 font-medium text-white">
                    {identity.name}
                  </td>
                  <td className="px-4 py-3 text-gray-400">{identity.type}</td>
                  <td className="px-4 py-3 text-gray-400">
                    {identity.last_activity
                      ? new Date(identity.last_activity).toLocaleDateString()
                      : "Never"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <RiskBadge score={identity.risk_score} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    {identity.is_quarantined ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-red-500/20 px-2 py-0.5 text-xs font-medium text-red-400">
                        <ShieldOff className="h-3 w-3" /> Quarantined
                      </span>
                    ) : (
                      <span className="text-xs text-green-500">Active</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleViewRecommendation(identity)}
                        className="inline-flex items-center gap-1 rounded-lg bg-surface-200 px-2.5 py-1.5 text-xs font-medium text-ghost-400 transition-colors hover:bg-ghost-600/20 hover:text-ghost-300"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        AI Rec
                      </button>
                      {!identity.is_quarantined && (
                        <button
                          onClick={() => handleQuarantine(identity.arn)}
                          disabled={quarantining === identity.arn}
                          className="inline-flex items-center gap-1 rounded-lg bg-red-500/10 px-2.5 py-1.5 text-xs font-medium text-red-400 transition-colors hover:bg-red-500/25 disabled:opacity-50"
                        >
                          {quarantining === identity.arn ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <ShieldOff className="h-3.5 w-3.5" />
                          )}
                          Quarantine
                        </button>
                      )}
                    </div>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
          </tbody>
        </table>

        {filtered.length === 0 && (
          <p className="py-12 text-center text-sm text-gray-600">
            No identities match the current filter.
          </p>
        )}
      </div>

      {/* Policy recommendation modal */}
      <PolicyModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        identityName={selectedIdentity?.name ?? ""}
        currentActions={selectedIdentity?.allowed_actions ?? []}
        analysis={analysis}
        loading={analysisLoading}
      />
    </>
  );
}
