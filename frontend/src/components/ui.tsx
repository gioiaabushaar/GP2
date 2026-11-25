import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

const cx = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(" ");

export function Logo({ className = "text-xl" }: { className?: string }) {
  return (
    <span className={cx("font-extrabold tracking-tight text-white", className)}>
      NEXIS<span className="text-accent">.</span>
    </span>
  );
}

export function Splash() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg">
      <div className="flex flex-col items-center gap-3">
        <Logo className="text-3xl" />
        <Spinner />
      </div>
    </div>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      aria-label="Loading"
      className={cx("inline-block h-5 w-5 animate-spin rounded-full border-2 border-line border-t-accent", className)}
    />
  );
}

export function PageHeader({ title, subtitle, actions }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4 border-b border-line pb-4">
      <div>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
    </div>
  );
}

export function Card({ title, children, className = "", actions }: { title?: ReactNode; children: ReactNode; className?: string; actions?: ReactNode }) {
  return (
    <section className={cx("min-w-0 rounded-xl border border-line bg-card p-5", className)}>
      {(title || actions) && (
        <div className="mb-3 flex items-center justify-between gap-3">
          {title && <h2 className="text-base font-semibold text-white">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function StatCard({ label, value, tone = "text-white", note }: { label: string; value: ReactNode; tone?: string; note?: string }) {
  return (
    <div className="rounded-xl border border-line bg-card p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className={cx("mt-2 text-3xl font-bold", tone)}>{value}</p>
      {note && <p className="mt-1 text-xs text-muted">{note}</p>}
    </div>
  );
}

const badgeTones = {
  accent: "bg-accent/15 text-accent",
  ok: "bg-ok/15 text-ok",
  warn: "bg-warn/15 text-warn",
  bad: "bg-bad/15 text-bad",
  hint: "bg-hint/15 text-hint",
  muted: "bg-white/5 text-muted",
} as const;

export function Badge({ tone = "accent", children }: { tone?: keyof typeof badgeTones; children: ReactNode }) {
  return <span className={cx("inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold", badgeTones[tone])}>{children}</span>;
}

export const difficultyTone = (d: string) => (d === "Easy" ? "ok" : d === "Medium" ? "warn" : "bad");

const buttonStyles = {
  primary: "bg-accent text-accent-ink hover:brightness-110",
  secondary: "border border-line bg-panel text-white hover:border-accent/60",
  ghost: "text-muted hover:text-white",
  danger: "bg-bad text-white hover:brightness-110",
} as const;

type ButtonProps = ComponentProps<"button"> & { variant?: keyof typeof buttonStyles; busy?: boolean };

export function Button({ variant = "primary", busy, className = "", children, disabled, ...rest }: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || busy}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50",
        buttonStyles[variant],
        className,
      )}
    >
      {busy && <Spinner className="h-4 w-4" />}
      {children}
    </button>
  );
}

export function ButtonLink({ href, variant = "primary", className = "", children }: { href: string; variant?: keyof typeof buttonStyles; className?: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className={cx("inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition", buttonStyles[variant], className)}
    >
      {children}
    </Link>
  );
}

const inputClass =
  "w-full rounded-lg border border-line bg-panel px-3 py-2 text-sm text-white placeholder:text-muted/70 outline-none focus:border-accent";

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm text-muted">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted/80">{hint}</span>}
    </label>
  );
}

export const Input = (props: ComponentProps<"input">) => <input {...props} className={cx(inputClass, props.className)} />;
export const Select = (props: ComponentProps<"select">) => <select {...props} className={cx(inputClass, props.className)} />;
export const Textarea = (props: ComponentProps<"textarea">) => <textarea {...props} className={cx(inputClass, "min-h-24", props.className)} />;

const noticeTones = {
  info: "border-accent/30 bg-accent/10 text-accent",
  ok: "border-ok/30 bg-ok/10 text-ok",
  warn: "border-warn/30 bg-warn/10 text-warn",
  bad: "border-bad/30 bg-bad/10 text-bad",
} as const;

export function Notice({ tone = "info", children }: { tone?: keyof typeof noticeTones; children: ReactNode }) {
  return <div className={cx("rounded-lg border px-4 py-3 text-sm", noticeTones[tone])}>{children}</div>;
}

/** Shown where the demo has a number the backend does not record yet. */
export function NotTracked({ why }: { why: string }) {
  return (
    <span className="text-muted" title={why}>
      —
    </span>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-dashed border-line px-4 py-6 text-center text-sm text-muted">{children}</p>;
}

export function ErrorText({ error }: { error: unknown }) {
  if (!error) return null;
  return <Notice tone="bad">{error instanceof Error ? error.message : String(error)}</Notice>;
}

export function Table({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-left text-sm">
        <thead>
          <tr className="border-b border-line text-xs uppercase tracking-wide text-muted">
            {head.map((h) => (
              <th key={h} className="px-3 py-2 font-semibold">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">{children}</tbody>
      </table>
    </div>
  );
}

export function Modal({ open, children }: { open: boolean; children: ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-md rounded-xl border border-ok/40 bg-card p-6 text-center shadow-2xl">{children}</div>
    </div>
  );
}
