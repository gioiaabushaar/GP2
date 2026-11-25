"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { homeFor, useAuth } from "@/lib/auth";
import { AuthCard } from "@/components/auth-card";
import { Button, ErrorText, Field, Input, Notice } from "@/components/ui";

export default function LoginPage() {
  const { user, login } = useAuth();
  const router = useRouter();
  const expired = useSearchParams().get("expired") === "1";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) router.replace(homeFor(user));
  }, [user, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const u = await login(email, password);
      router.replace(homeFor(u));
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <AuthCard title="Portal Access">
      <form onSubmit={onSubmit} className="space-y-4">
        {expired && <Notice tone="warn">Your session expired. Please log in again.</Notice>}
        <Field label="Email Address">
          <Input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
        </Field>
        <Field label="Password">
          <Input type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <ErrorText error={error} />
        <Button type="submit" busy={busy} className="w-full">
          Login
        </Button>
        <p className="text-center text-xs text-muted">
          Students and instructors use the same login. You are taken to your own dashboard.
        </p>
        <p className="text-center text-sm">
          <Link href="/register" className="text-accent hover:underline">
            Create a student account
          </Link>
        </p>
      </form>
    </AuthCard>
  );
}
