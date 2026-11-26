"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { riskFor } from "@/lib/insights";
import { Badge, Card, EmptyState, ErrorText, PageHeader, Spinner, StatCard, Table } from "@/components/ui";

export default function InstructorDashboard() {
  const overview = useQuery({ queryKey: ["overview"], queryFn: api.instructorOverview });
  const board = useQuery({ queryKey: ["leaderboard"], queryFn: api.leaderboard });
  const recent = useQuery({ queryKey: ["deployments"], queryFn: api.deployments });

  const o = overview.data;
  const successRate = o && o.submissions ? Math.round((o.correct_submissions / o.submissions) * 100) : null;
  const atRisk = board.data && o ? board.data.filter((s) => riskFor(s.solved_count, o.challenges) === "High").length : null;
  const waiting = overview.isPending || board.isPending;
  const loading = (v: number | null | undefined) => v ?? (waiting ? <Spinner /> : "—");

  return (
    <>
      <PageHeader title="Instructor Operations" subtitle="Real-time telemetry and student analytics." />
      <ErrorText error={overview.error ?? board.error} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Students" value={loading(o?.students)} />
        <StatCard label="Published Challenges" value={loading(o?.challenges)} tone="text-ok" />
        <StatCard label="Avg. Success Rate" value={successRate === null ? loading(null) : `${successRate}%`} tone="text-accent" note={o ? `${o.correct_submissions} correct of ${o.submissions} flag attempts` : undefined} />
        <StatCard label="Students at Risk" value={loading(atRisk)} tone="text-bad" note="Solved under 40% of challenges" />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card title="Recent Lab Deployments" actions={<Badge tone="warn">Simulated</Badge>}>
          {recent.isPending ? (
            <Spinner />
          ) : !recent.data?.length ? (
            <EmptyState>No deployments yet. Use Deploy Labs to run one.</EmptyState>
          ) : (
            <Table head={["Module", "Containers", "Status"]}>
              {recent.data.slice(0, 5).map((d) => (
                <tr key={d.id}>
                  <td className="px-3 py-2">{d.challenge_title}</td>
                  <td className="px-3 py-2">{d.status === "running" ? d.students : 0}</td>
                  <td className={`px-3 py-2 ${d.status === "running" ? "text-ok" : "text-bad"}`}>{d.status === "running" ? "Running" : "Refused"}</td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card title="Top Students">
          {board.isPending ? (
            <Spinner />
          ) : !board.data?.length ? (
            <EmptyState>No students registered yet.</EmptyState>
          ) : (
            <Table head={["Rank", "Student", "Score", "Solved"]}>
              {board.data.slice(0, 5).map((s) => (
                <tr key={s.user_id}>
                  <td className="px-3 py-2">{s.rank}</td>
                  <td className="px-3 py-2 text-white">{s.full_name}</td>
                  <td className="px-3 py-2 text-accent">{s.total_score}</td>
                  <td className="px-3 py-2">{s.solved_count}</td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card title="Platform Activity">
          <dl className="space-y-1 text-sm">
            <div>
              <dt className="inline text-muted">Flag attempts: </dt>
              <dd className="inline">{loading(o?.submissions)}</dd>
            </div>
            <div>
              <dt className="inline text-muted">Correct flags: </dt>
              <dd className="inline text-ok">{loading(o?.correct_submissions)}</dd>
            </div>
            <div>
              <dt className="inline text-muted">Mentor hints requested: </dt>
              <dd className="inline text-hint">{loading(o?.hints_requested)}</dd>
            </div>
          </dl>
        </Card>

        <Card title="Most Failed Challenges">
          <EmptyState>Shown once the backend reports results per challenge (FR8, curriculum metrics).</EmptyState>
        </Card>
      </div>
    </>
  );
}
