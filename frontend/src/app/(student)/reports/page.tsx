"use client";

import Link from "next/link";
import { useQueries, useQuery } from "@tanstack/react-query";
import { ApiError, api } from "@/lib/api";
import { learningPattern } from "@/lib/insights";
import { Badge, EmptyState, ErrorText, PageHeader, Spinner, Table } from "@/components/ui";

export default function ReportsList() {
  const challenges = useQuery({ queryKey: ["challenges", {}], queryFn: () => api.challenges() });
  const reports = useQueries({
    queries: (challenges.data ?? []).map((c) => ({
      queryKey: ["report", c.id],
      queryFn: () => api.report(c.id).catch((e) => (e instanceof ApiError && e.status === 404 ? null : Promise.reject(e))),
    })),
  });

  const loading = challenges.isPending || reports.some((r) => r.isPending);
  const rows = reports.map((r) => r.data).filter((r) => r != null);

  return (
    <>
      <PageHeader title="Reports" subtitle="A post-challenge report for every challenge you worked on." />
      <ErrorText error={challenges.error ?? reports.find((r) => r.error)?.error} />
      {loading ? (
        <Spinner />
      ) : rows.length === 0 ? (
        <EmptyState>No reports yet. Reports appear after you submit a flag or ask the mentor for a hint.</EmptyState>
      ) : (
        <div className="rounded-xl border border-line bg-card p-2">
          <Table head={["Challenge", "Status", "Attempts", "Hints", "Pattern", ""]}>
            {rows.map((r) => (
              <tr key={r.challenge_id}>
                <td className="px-3 py-3 font-medium text-white">{r.title}</td>
                <td className="px-3 py-3">{r.solved ? <Badge tone="ok">Solved</Badge> : <Badge tone="warn">In progress</Badge>}</td>
                <td className="px-3 py-3">{r.attempts}</td>
                <td className="px-3 py-3">{r.hints_used}</td>
                <td className="px-3 py-3 text-accent">{learningPattern({ solved: r.solved, attempts: r.attempts, hints: r.hints_used })}</td>
                <td className="px-3 py-3 text-right">
                  <Link href={`/reports/${r.challenge_id}`} className="font-semibold text-accent hover:underline">
                    View report
                  </Link>
                </td>
              </tr>
            ))}
          </Table>
        </div>
      )}
    </>
  );
}
