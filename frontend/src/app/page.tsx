"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { RefreshCw, Scan } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import StatsBar from "@/components/StatsBar";
import IdentityTable from "@/components/IdentityTable";
import { fetchIdentities, triggerScan, type Identity } from "@/lib/api";

export default function DashboardPage() {
  const [identities, setIdentities] = useState<Identity[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchIdentities();
      setIdentities(data);
    } catch (err) {
      console.error("Failed to load identities:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleScan = async () => {
    setScanning(true);
    try {
      await triggerScan();
      await loadData();
    } catch (err) {
      console.error("Scan failed:", err);
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <main className="ml-64 flex-1 p-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">
              Identity Risk Dashboard
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              Non-Human Identity audit & least-privilege enforcement
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={loadData}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-surface-200 px-4 py-2 text-sm font-medium text-gray-300 transition-colors hover:bg-surface-300 disabled:opacity-50"
            >
              <RefreshCw
                className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
              />
              Refresh
            </button>
            <button
              onClick={handleScan}
              disabled={scanning}
              className="inline-flex items-center gap-2 rounded-lg bg-ghost-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-ghost-700 disabled:opacity-50"
            >
              <Scan
                className={`h-4 w-4 ${scanning ? "animate-spin" : ""}`}
              />
              {scanning ? "Scanning…" : "Scan AWS"}
            </button>
          </div>
        </div>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <StatsBar identities={identities} />
        </motion.div>

        {/* Table */}
        <motion.div
          className="mt-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
        >
          {loading ? (
            <div className="flex items-center justify-center py-24">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-ghost-400 border-t-transparent" />
            </div>
          ) : (
            <IdentityTable identities={identities} onRefresh={loadData} />
          )}
        </motion.div>
      </main>
    </div>
  );
}
