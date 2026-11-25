"use client";

import { useEffect, useState } from "react";

export function formatClock(totalSeconds: number) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(sec).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

/** Re-renders every second and returns whole seconds left until `endsAt` (ms). */
export function useSecondsLeft(endsAt: number | null) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (endsAt === null) return;
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, [endsAt]);
  return endsAt === null ? null : Math.max(0, Math.round((endsAt - now) / 1000));
}

export function Countdown({ endsAt, className = "" }: { endsAt: number | null; className?: string }) {
  const left = useSecondsLeft(endsAt);
  if (left === null) return <span className={`font-mono text-2xl text-muted ${className}`}>--:--</span>;
  const tone = left === 0 ? "text-bad" : left < 300 ? "text-warn" : "text-ok";
  return (
    <span className={`font-mono text-2xl font-bold ${tone} ${className}`} aria-live="polite">
      {left === 0 ? "Expired" : formatClock(left)}
    </span>
  );
}

/** Seconds since the component mounted, ticking once per second. */
export function useElapsedSeconds() {
  const [start] = useState(() => Date.now());
  const [now, setNow] = useState(start);
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);
  return Math.floor((now - start) / 1000);
}
