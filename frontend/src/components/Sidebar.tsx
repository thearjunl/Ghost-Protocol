"use client";

import { Shield, Scan, Activity, AlertTriangle } from "lucide-react";
import Link from "next/link";

const navItems = [
  { label: "Dashboard", href: "/", icon: Shield },
  { label: "Scan", href: "#scan", icon: Scan },
  { label: "Activity", href: "#activity", icon: Activity },
  { label: "Alerts", href: "#alerts", icon: AlertTriangle },
];

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-64 flex-col border-r border-surface-300 bg-surface">
      {/* Brand */}
      <div className="flex items-center gap-3 border-b border-surface-300 px-6 py-5">
        <Shield className="h-8 w-8 text-ghost-400" />
        <div>
          <h1 className="text-lg font-bold tracking-tight text-white">
            GhostProtocol
          </h1>
          <p className="text-xs text-gray-500">NHI Security Platform</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => (
          <Link
            key={item.label}
            href={item.href}
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-gray-400 transition-colors hover:bg-surface-200 hover:text-white"
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-surface-300 px-6 py-4">
        <p className="text-xs text-gray-600">v0.1.0 · Audit Engine Active</p>
      </div>
    </aside>
  );
}
