"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { riskFor, riskTone } from "@/lib/insights";
import { Badge, Button, Card, EmptyState, ErrorText, PageHeader, Spinner, Table } from "@/components/ui";

export default function StudentInsights() {
  const board = useQuery({ queryKey: ["leaderboard"], queryFn: api.leaderboard });
  const overview = useQuery({ queryKey: ["overview"], queryFn: api.instructorOverview });
  const [selected, setSelected] = useState<number | null>(null);
  const total = overview.data?.challenges ?? 0;
  const student = board.data?.find((s) => s.user_id === selected);

  return (
    <>
      <PageHeader title="Student Behavioral Insights" subtitle="Progress and risk for every student, ranked by score." />
      <ErrorText error={board.error ?? overview.error} />
      <Card>
        {board.isPending || overview.isPending ? (
          <Spinner />
        ) : !board.data?.length ? (
          <EmptyState>No students registered yet.</EmptyState>
        ) : (
          <Table head={["Student Name", "Completed", "Score", "Learning Pattern", "Risk Level", "Action"]}>
            {board.data.map((s) => {
              const risk = riskFor(s.solved_count, total);
              return (
                <tr key={s.user_id} className={s.user_id === selected ? "bg-white/5" : undefined}>
                  <td className="px-3 py-3 text-white">{s.full_name}</td>
                  <td className="px-3 py-3">
                    {s.solved_count} / {total}
                  </td>
                  <td className="px-3 py-3 text-accent">{s.total_score}</td>
                  <td className="px-3 py-3 text-muted" title="Needs per-student behaviour events (FR7)">
                    Not tracked yet
                  </td>
                  <td className="px-3 py-3">
                    <Badge tone={riskTone(risk)}>{risk}</Badge>
                  </td>
                  <td className="px-3 py-3">
                    <Button variant="secondary" className="px-3 py-1" onClick={() => setSelected(s.user_id === selected ? null : s.user_id)}>
                      {s.user_id === selected ? "Hide" : "View"}
                    </Button>
                  </td>
                </tr>
              );
            })}
          </Table>
        )}
      </Card>

      {student && (
        <Card title={`Profile Insight: ${student.full_name}`} className="mt-4 border-accent/50">
          <div className="grid gap-4 text-sm md:grid-cols-2">
            <dl className="space-y-1">
              <div>
                <dt className="inline font-semibold">Rank: </dt>
                <dd className="inline">
                  #{student.rank} of {board.data?.length}
                </dd>
              </div>
              <div>
                <dt className="inline font-semibold">Score: </dt>
                <dd className="inline">{student.total_score} points</dd>
              </div>
              <div>
                <dt className="inline font-semibold">Completed: </dt>
                <dd className="inline">
                  {student.solved_count} of {total} challenges ({total ? Math.round((student.solved_count / total) * 100) : 0}%)
                </dd>
              </div>
            </dl>
            <dl className="space-y-1">
              <div>
                <dt className="inline font-semibold">Risk: </dt>
                <dd className="inline">
                  {riskFor(student.solved_count, total)} (High means under 40% of challenges solved)
                </dd>
              </div>
              <div>
                <dt className="inline font-semibold">Strength / Weakness: </dt>
                <dd className="inline text-muted">needs per-category results from the backend</dd>
              </div>
              <div>
                <dt className="inline font-semibold">Recommendation: </dt>
                <dd className="inline">
                  {riskFor(student.solved_count, total) === "High" ? "Check in with this student and suggest an Easy challenge." : "On track. Suggest a harder challenge next."}
                </dd>
              </div>
            </dl>
          </div>
        </Card>
      )}
    </>
  );
}
