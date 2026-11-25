"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/insights";
import type { WebAttempt } from "@/lib/types";
import { formatClock } from "@/components/countdown";
import { Badge, Button, Card, EmptyState, ErrorText, PageHeader, Select, Spinner, Table } from "@/components/ui";

function StatusBadge({ a }: { a: WebAttempt }) {
  if (a.status === "active") return <Badge tone="warn">Running · {formatClock(a.seconds_left)}</Badge>;
  if (a.status === "locked") return <Badge tone="bad">Locked</Badge>;
  return <Badge tone="muted">Unlocked</Badge>;
}

export default function WebLabExams() {
  const qc = useQueryClient();
  const [quiz, setQuiz] = useState("");
  const exams = useQuery({ queryKey: ["web-exams"], queryFn: api.webExams });
  const attempts = useQuery({
    queryKey: ["web-attempts", quiz],
    queryFn: () => api.allExamAttempts(quiz || undefined),
    refetchInterval: 10_000, // live view while students sit the exam
  });
  const unlock = useMutation({
    mutationFn: (id: number) => api.unlockExam(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["web-attempts"] }),
  });

  const rows = attempts.data ?? [];
  const lockedCount = rows.filter((a) => a.status === "locked").length;
  const runningCount = rows.filter((a) => a.status === "active").length;

  return (
    <>
      <PageHeader
        title="Web Lab Exams"
        subtitle="Live view of the PortSwigger exams. Unlock a station to let the student sit an exam again."
        actions={
          <Select value={quiz} onChange={(e) => setQuiz(e.target.value)} aria-label="Exam" className="w-44">
            <option value="">All exams</option>
            {(exams.data ?? []).map((q) => (
              <option key={q.id} value={q.id}>
                {q.title}
              </option>
            ))}
          </Select>
        }
      />
      <ErrorText error={attempts.error ?? exams.error ?? unlock.error} />
      <p className="mb-3 text-sm text-muted">
        {runningCount} running · {lockedCount} locked · refreshes every 10 seconds. Solved marks are reported by the student; check their PortSwigger screen to confirm.
      </p>

      <Card>
        {attempts.isPending ? (
          <Spinner />
        ) : rows.length === 0 ? (
          <EmptyState>No exam attempts yet.</EmptyState>
        ) : (
          <Table head={["Student", "Exam", "Status", "Assigned labs", "Solved", "Started"]}>
            {rows.map((a) => (
              <tr key={a.id} className="align-top">
                <td className="px-3 py-3">
                  <p className="text-white">{a.student?.full_name}</p>
                  <p className="text-xs text-muted">{a.student?.email}</p>
                </td>
                <td className="px-3 py-3">{a.quiz_title}</td>
                <td className="px-3 py-3">
                  <div className="flex flex-col items-start gap-2">
                    <StatusBadge a={a} />
                    {a.status !== "reset" && (
                      <Button
                        variant={a.status === "locked" ? "primary" : "secondary"}
                        className="px-3 py-1"
                        busy={unlock.isPending && unlock.variables === a.id}
                        onClick={() => {
                          const msg =
                            a.status === "active"
                              ? `${a.student?.full_name} is still taking this exam. Unlock and reset it now?`
                              : `Unlock ${a.student?.full_name}'s station so they can start an exam again?`;
                          if (window.confirm(msg)) unlock.mutate(a.id);
                        }}
                      >
                        Unlock
                      </Button>
                    )}
                  </div>
                </td>
                <td className="px-3 py-3">
                  <ol className="min-w-64 space-y-1 text-xs">
                    {a.labs.map((l) => (
                      <li key={l.index} className={l.solved ? "text-ok" : "text-muted"}>
                        {l.solved ? "✓" : "○"}{" "}
                        <a href={l.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                          {l.title}
                        </a>
                      </li>
                    ))}
                  </ol>
                </td>
                <td className="px-3 py-3 font-semibold text-white">
                  {a.solved_count} / {a.labs.length}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-xs text-muted">{formatDate(a.started_at)}</td>
              </tr>
            ))}
          </Table>
        )}
      </Card>

      <Card title="Exam lab pools" className="mt-6">
        <div className="space-y-2">
          {(exams.data ?? []).map((q) => (
            <details key={q.id} className="rounded-lg border border-line bg-panel">
              <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-white">
                {q.title}: {q.pool_size} labs, {q.labs_per_attempt} drawn at random, {q.duration_minutes} minutes
              </summary>
              <ol className="list-decimal space-y-1 border-t border-line py-3 pl-10 pr-4 text-sm">
                {(q.pool ?? []).map((l) => (
                  <li key={l.url}>
                    <a href={l.url} target="_blank" rel="noopener noreferrer" className="hover:text-accent hover:underline">
                      {l.title}
                    </a>
                  </li>
                ))}
              </ol>
            </details>
          ))}
        </div>
      </Card>
    </>
  );
}
