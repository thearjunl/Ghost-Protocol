"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, AlertCircle, CheckCircle2, Info } from "lucide-react";

export type ToastType = "error" | "success" | "info";

export interface ToastMessage {
  id: string;
  type: ToastType;
  text: string;
}

const icons: Record<ToastType, typeof AlertCircle> = {
  error: AlertCircle,
  success: CheckCircle2,
  info: Info,
};

const colors: Record<ToastType, string> = {
  error: "border-red-500/40 bg-red-500/10 text-red-300",
  success: "border-green-500/40 bg-green-500/10 text-green-300",
  info: "border-ghost-500/40 bg-ghost-500/10 text-ghost-300",
};

// ── Global toast state (simple pub/sub) ────────────────────────────────
type Listener = (msgs: ToastMessage[]) => void;
let toasts: ToastMessage[] = [];
const listeners = new Set<Listener>();

function emit() {
  listeners.forEach((l) => l([...toasts]));
}

export function toast(type: ToastType, text: string) {
  const id = crypto.randomUUID();
  toasts = [...toasts, { id, type, text }];
  emit();
  setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== id);
    emit();
  }, 5000);
}

// ── Component ──────────────────────────────────────────────────────────
export default function ToastContainer() {
  const [messages, setMessages] = useState<ToastMessage[]>([]);

  useEffect(() => {
    listeners.add(setMessages);
    return () => {
      listeners.delete(setMessages);
    };
  }, []);

  const dismiss = (id: string) => {
    toasts = toasts.filter((t) => t.id !== id);
    emit();
  };

  return (
    <div className="pointer-events-none fixed bottom-6 right-6 z-[100] flex flex-col gap-2">
      <AnimatePresence>
        {messages.map((msg) => {
          const Icon = icons[msg.type];
          return (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              className={`pointer-events-auto flex items-start gap-2 rounded-lg border px-4 py-3 shadow-lg backdrop-blur ${colors[msg.type]}`}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" />
              <span className="text-sm">{msg.text}</span>
              <button
                onClick={() => dismiss(msg.id)}
                className="ml-2 shrink-0 rounded p-0.5 hover:bg-white/10"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
