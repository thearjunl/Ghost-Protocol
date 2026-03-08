"use client";

import { Fragment } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import type { AnalysisResult } from "@/lib/api";

interface PolicyModalProps {
  open: boolean;
  onClose: () => void;
  identityName: string;
  currentActions: string[];
  analysis: AnalysisResult | null;
  loading: boolean;
}

export default function PolicyModal({
  open,
  onClose,
  identityName,
  currentActions,
  analysis,
  loading,
}: PolicyModalProps) {
  return (
    <AnimatePresence>
      {open && (
        <Fragment>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
          >
            <div className="relative max-h-[80vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-surface-300 bg-surface-100 p-6 shadow-2xl">
              {/* Close */}
              <button
                onClick={onClose}
                className="absolute right-4 top-4 rounded-lg p-1 text-gray-500 hover:bg-surface-300 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>

              <h2 className="mb-1 text-lg font-bold text-white">
                AI Policy Recommendation
              </h2>
              <p className="mb-6 text-sm text-gray-500">{identityName}</p>

              {loading ? (
                <div className="flex items-center justify-center py-16">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-ghost-400 border-t-transparent" />
                  <span className="ml-3 text-sm text-gray-400">
                    Analysing with Ollama…
                  </span>
                </div>
              ) : analysis ? (
                <div className="grid gap-6 md:grid-cols-2">
                  {/* Current policy */}
                  <div>
                    <h3 className="mb-2 text-sm font-semibold text-red-400">
                      Current Actions ({currentActions.length})
                    </h3>
                    <pre className="max-h-64 overflow-auto rounded-lg bg-surface p-3 font-mono text-xs text-gray-300">
                      {JSON.stringify(currentActions, null, 2)}
                    </pre>
                  </div>

                  {/* Recommended policy */}
                  <div>
                    <h3 className="mb-2 text-sm font-semibold text-green-400">
                      Recommended Policy
                    </h3>
                    <pre className="max-h-64 overflow-auto rounded-lg bg-surface p-3 font-mono text-xs text-gray-300">
                      {JSON.stringify(analysis.recommended_policy, null, 2)}
                    </pre>
                  </div>

                  {/* Summary */}
                  <div className="md:col-span-2">
                    <h3 className="mb-2 text-sm font-semibold text-ghost-400">
                      Risk Assessment — Score: {analysis.risk_score}/100
                    </h3>
                    <p className="rounded-lg bg-surface p-3 text-sm text-gray-300">
                      {analysis.summary}
                    </p>
                    {analysis.unused_actions.length > 0 && (
                      <details className="mt-3">
                        <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-300">
                          {analysis.unused_actions.length} unused action(s)
                        </summary>
                        <pre className="mt-1 max-h-32 overflow-auto rounded-lg bg-surface p-2 font-mono text-xs text-yellow-400/80">
                          {analysis.unused_actions.join("\n")}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-gray-500">
                  No analysis data available.
                </p>
              )}
            </div>
          </motion.div>
        </Fragment>
      )}
    </AnimatePresence>
  );
}
