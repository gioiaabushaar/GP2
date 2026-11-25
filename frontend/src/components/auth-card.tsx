import type { ReactNode } from "react";
import { Logo } from "./ui";

export function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <Logo className="text-4xl" />
      <p className="mt-2 text-sm text-muted">Interactive Cybersecurity Learning Platform</p>
      <div className="mt-8 w-full max-w-sm rounded-xl border border-line bg-card p-6">
        <h1 className="mb-4 text-xl font-bold text-white">{title}</h1>
        {children}
      </div>
    </div>
  );
}
