"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";
import { AuthCard } from "@/components/auth-card";
import { Button, ErrorText, Field, Input } from "@/components/ui";

export default function RegisterPage() {
  const { user, login } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) router.replace(homeFor(user));
  }, [user, router]);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.register(form.full_name, form.email, form.password);
      const u = await login(form.email, form.password);
      router.replace(homeFor(u));
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <AuthCard title="Create Student Account">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Full Name">
          <Input required minLength={2} value={form.full_name} onChange={set("full_name")} autoComplete="name" />
        </Field>
        <Field label="Email Address">
          <Input type="email" required value={form.email} onChange={set("email")} autoComplete="email" />
        </Field>
        <Field label="Password" hint="At least 10 characters.">
          <Input type="password" required minLength={10} value={form.password} onChange={set("password")} autoComplete="new-password" />
        </Field>
        <ErrorText error={error} />
        <Button type="submit" busy={busy} className="w-full">
          Create Account
        </Button>
        <p className="text-center text-sm">
          <Link href="/login" className="text-accent hover:underline">
            I already have an account
          </Link>
        </p>
      </form>
    </AuthCard>
  );
}
