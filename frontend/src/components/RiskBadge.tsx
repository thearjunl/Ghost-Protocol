"use client";

import { cn } from "@/lib/utils";

interface RiskBadgeProps {
  score: number;
  className?: string;
}

export default function RiskBadge({ score, className }: RiskBadgeProps) {
  const color =
    score > 80
      ? "bg-red-500/20 text-red-400 border-red-500/30"
      : score > 50
        ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
        : "bg-green-500/20 text-green-400 border-green-500/30";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        color,
        className,
      )}
    >
      {score}
    </span>
  );
}
