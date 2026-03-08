"use client";

import { Shield, AlertTriangle, Activity, ShieldOff } from "lucide-react";
import type { Identity } from "@/lib/api";

interface Props {
  identities: Identity[];
}

export default function StatsBar({ identities }: Props) {
  const total = identities.length;
  const critical = identities.filter((i) => i.risk_score > 80).length;
  const quarantined = identities.filter((i) => i.is_quarantined).length;
  const avgRisk =
    total > 0
      ? Math.round(identities.reduce((s, i) => s + i.risk_score, 0) / total)
      : 0;

  const cards = [
    {
      label: "Total NHIs",
      value: total,
      icon: Shield,
      color: "text-ghost-400",
    },
    {
      label: "Critical Risk",
      value: critical,
      icon: AlertTriangle,
      color: "text-red-400",
    },
    {
      label: "Avg Risk Score",
      value: avgRisk,
      icon: Activity,
      color: "text-yellow-400",
    },
    {
      label: "Quarantined",
      value: quarantined,
      icon: ShieldOff,
      color: "text-orange-400",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((c) => (
        <div
          key={c.label}
          className="rounded-xl border border-surface-300 bg-surface-100 p-4"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">{c.label}</p>
            <c.icon className={`h-4 w-4 ${c.color}`} />
          </div>
          <p className="mt-2 text-2xl font-bold text-white">{c.value}</p>
        </div>
      ))}
    </div>
  );
}
