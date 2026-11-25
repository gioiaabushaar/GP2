"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, lastLab, levelFor } from "@/lib/insights";
import { Badge, ButtonLink, Card, EmptyState, ErrorText, PageHeader, Spinner, StatCard } from "@/components/ui";

export default function StudentDashboard() {
  const { user } = useAuth();
  const score = useQuery({ queryKey: ["my-score"], queryFn: api.myScore });
  const activity = useQuery({ queryKey: ["my-activity"], queryFn: api.myActivity });
  const labs = useQuery({ queryKey: ["my-labs"], queryFn: api.myLabs });
  const challenges = useQuery({ queryKey: ["challenges", {}], queryFn: () => api.challenges() });
  const continueId = lastLab.get();

  const titleOf = (id: number) => challenges.data?.find((c) => c.id === id)?.title ?? `Challenge #${id}`;
  const events = [
    ...(score.data?.solved ?? []).map((s) => ({ at: s.solved_at, text: `Completed "${s.title}" (+${s.points} pts)` })),
    ...(labs.data ?? []).map((l) => ({ at: l.started_at, text: `Started a lab for "${titleOf(l.challenge_id)}"` })),
  ]
    .sort((a, b) => b.at.localeCompare(a.at))
    .slice(0, 6);

  const firstName = user?.full_name.split(" ")[0] ?? "";
  const total = score.data?.total_score ?? 0;

  return (
    <>
      <PageHeader
        title={`Welcome back, ${firstName}`}
        subtitle={
          <span className="flex items-center gap-2">
            Current Level: <Badge>{levelFor(total)}</Badge>
          </span>
        }
      />
      <ErrorText error={score.error ?? activity.error} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Score" value={score.isPending ? <Spinner /> : total} tone="text-accent" />
        <StatCard label="Challenges Completed" value={score.isPending ? <Spinner /> : score.data?.solved_count ?? 0} tone="text-ok" />
        <StatCard label="Hints Used" value={activity.isPending ? <Spinner /> : activity.data?.hints_used ?? 0} tone="text-hint" />
        <StatCard label="Flag Attempts" value={activity.isPending ? <Spinner /> : activity.data?.attempts ?? 0} />
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <ButtonLink href="/challenges">Browse Challenges</ButtonLink>
        <ButtonLink href="/reports" variant="secondary">
          View Reports
        </ButtonLink>
        {continueId && (
          <ButtonLink href={`/lab/${continueId}`} variant="secondary">
            Continue Active Lab
          </ButtonLink>
        )}
      </div>

      <Card title="Recent Activity" className="mt-6">
        {score.isPending || labs.isPending ? (
          <Spinner />
        ) : events.length ? (
          <ul className="space-y-2 text-sm">
            {events.map((e, i) => (
              <li key={i} className="flex flex-wrap justify-between gap-2">
                <span>{e.text}</span>
                <span className="text-muted">{formatDate(e.at)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>No activity yet. Pick a challenge to get started.</EmptyState>
        )}
      </Card>
    </>
  );
}
