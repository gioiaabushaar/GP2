"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { learningPattern } from "@/lib/insights";
import type { ChallengeReport } from "@/lib/types";
import { ButtonLink, EmptyState, ErrorText, Spinner } from "@/components/ui";

function strengths(r: ChallengeReport) {
  const out: string[] = [];
  if (r.solved) out.push("Captured the flag and completed the challenge.");
  if (r.solved && r.attempts <= 2) out.push("Reached the answer with very few flag attempts.");
  if (r.hints_used === 0) out.push("Worked independently without asking the mentor.");
  if (!r.solved && r.attempts > 0) out.push("Kept testing ideas instead of giving up.");
  return out.length ? out : ["Opened the challenge and started exploring it."];
}

function observations(r: ChallengeReport) {
  const out: string[] = [];
  if (r.hints_used >= 3) out.push("You depended heavily on hints. Try to form your own hypothesis before asking.");
  if (r.attempts >= 4 && !r.solved) out.push("Many flag attempts without success: focus on method rather than guessing.");
  if (r.attempts - (r.solved ? 1 : 0) >= 3) out.push("Several wrong flags were submitted before the right one.");
  return out.length ? out : ["No weak spots recorded for this challenge."];
}

export default function ReportPage() {
  const id = Number(useParams<{ id: string }>().id);
  const { user } = useAuth();
  const report = useQuery({ queryKey: ["report", id], queryFn: () => api.report(id), enabled: Number.isInteger(id) });
  const challenges = useQuery({ queryKey: ["challenges", {}], queryFn: () => api.challenges() });
  const points = challenges.data?.find((c) => c.id === id)?.points;

  if (report.isPending) return <Spinner />;
  if (report.error instanceof ApiError && report.error.status === 404) {
    return (
      <>
        <EmptyState>There is no activity for this challenge yet, so there is no report.</EmptyState>
        <div className="mt-4">
          <ButtonLink href={`/lab/${id}`}>Open the challenge</ButtonLink>
        </div>
      </>
    );
  }
  if (report.error) return <ErrorText error={report.error} />;
  const r = report.data;
  const pattern = learningPattern({ solved: r.solved, attempts: r.attempts, hints: r.hints_used });

  return (
    <article className="mx-auto max-w-4xl rounded-xl border border-line bg-card p-6 md:p-8">
      <h1 className="text-2xl font-bold text-white">{r.title}</h1>
      <p className="mt-1 text-muted">
        Student: {user?.full_name} | Final Score:{" "}
        {r.solved ? <span className="font-semibold text-ok">+{points ?? "?"}</span> : <span className="text-warn">not solved yet</span>}
      </p>
      <div className="mt-4 flex flex-wrap gap-2 text-sm">
        <Chip>Attempts: {r.attempts}</Chip>
        <Chip>Hints: {r.hints_used}</Chip>
        <Chip>Pattern: {pattern}</Chip>
      </div>

      <Section title="A. Summary">
        <p>{r.feedback}</p>
      </Section>
      <Section title="B. What You Did Well">
        <List items={strengths(r)} />
      </Section>
      <Section title="C. Weaknesses / Observations">
        <List items={observations(r)} />
      </Section>
      <Section title="D. Next Steps and Related Concepts">
        <List items={r.next_steps} />
        {r.learning_reference && <p className="mt-2 text-sm text-muted">Reference: {r.learning_reference}</p>}
      </Section>

      <p className="mt-6 text-xs text-muted">Report type: rule-based, built from your recorded attempts and hints.</p>
      <div className="mt-6 flex flex-wrap gap-3">
        <ButtonLink href="/dashboard">Return to Dashboard</ButtonLink>
        <ButtonLink href="/reports" variant="secondary">
          All Reports
        </ButtonLink>
      </div>
    </article>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return <span className="rounded-md bg-white/5 px-3 py-1 font-semibold text-white">{children}</span>;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="mb-2 text-lg font-bold text-white">{title}</h2>
      <div className="text-[15px] leading-relaxed text-text">{children}</div>
    </section>
  );
}

function List({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1 pl-5">
      {items.map((i) => (
        <li key={i}>{i}</li>
      ))}
    </ul>
  );
}
