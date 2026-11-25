"use client";

import Link from "next/link";
import { useDeferredValue, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatClock } from "@/components/countdown";
import { Badge, ButtonLink, Card, EmptyState, ErrorText, Input, Notice, PageHeader, Select, Spinner } from "@/components/ui";

export default function WebLabs() {
  const exams = useQuery({ queryKey: ["web-exams"], queryFn: api.webExams });
  const current = useQuery({ queryKey: ["web-exam-current"], queryFn: api.currentExam });
  const library = useQuery({ queryKey: ["web-library"], queryFn: api.webLibrary, staleTime: Infinity });
  const [search, setSearch] = useState("");
  const [topic, setTopic] = useState("");
  const query = useDeferredValue(search.trim().toLowerCase());

  const topics = (library.data?.topics ?? [])
    .filter((t) => !topic || t.name === topic)
    .map((t) => ({ ...t, labs: t.labs.filter((l) => !query || l.title.toLowerCase().includes(query) || t.name.toLowerCase().includes(query)) }))
    .filter((t) => t.labs.length);
  const shown = topics.reduce((n, t) => n + t.labs.length, 0);
  const open = current.data;

  return (
    <>
      <PageHeader title="Web Labs" subtitle="PortSwigger Web Security Academy labs, organised for NEXIS: timed exams and the full practice library." />

      {open && (
        <div className="mb-6">
          {open.status === "active" ? (
            <Notice tone="warn">
              Your {open.quiz_title} exam is running ({formatClock(open.seconds_left)} left).{" "}
              <Link href={`/web-labs/exam/${open.quiz_id}`} className="font-semibold underline">
                Return to the exam
              </Link>
            </Notice>
          ) : (
            <Notice tone="bad">
              Your {open.quiz_title} exam is locked. Ask the instructor to unlock it before starting another exam.{" "}
              <Link href={`/web-labs/exam/${open.quiz_id}`} className="font-semibold underline">
                Open it
              </Link>
            </Notice>
          )}
        </div>
      )}

      <h2 className="mb-3 text-lg font-semibold text-white">Timed Exams</h2>
      <ErrorText error={exams.error ?? current.error} />
      {exams.isPending ? (
        <Spinner />
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {(exams.data ?? []).map((q) => (
            <article key={q.id} className="flex flex-col rounded-xl border border-line bg-card p-5">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-lg font-bold text-white">{q.title}</h3>
                {open?.quiz_id === q.id && <Badge tone={open.status === "active" ? "warn" : "bad"}>{open.status === "active" ? "Running" : "Locked"}</Badge>}
              </div>
              <p className="mt-2 text-sm text-muted">{q.description}</p>
              <p className="mt-3 text-sm">
                <span className="text-accent">{q.duration_minutes} minutes</span> · {q.labs_per_attempt} random labs out of {q.pool_size}
              </p>
              <div className="mt-auto pt-4">
                <ButtonLink href={`/web-labs/exam/${q.id}`} variant={open && open.quiz_id !== q.id ? "secondary" : "primary"}>
                  {open?.quiz_id === q.id ? "Open Exam" : "View Instructions"}
                </ButtonLink>
              </div>
            </article>
          ))}
        </div>
      )}

      <Card
        className="mt-8"
        title={`Practice Library${library.data ? ` (${shown} of ${library.data.total} labs)` : ""}`}
        actions={<Badge tone="muted">Opens on portswigger.net</Badge>}
      >
        <p className="-mt-1 mb-4 text-sm text-muted">
          Every lab runs on PortSwigger&apos;s own site and needs a free PortSwigger account. Use Burp Suite while you work.
        </p>
        <div className="mb-4 grid gap-3 sm:grid-cols-2">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search labs, e.g. union, CSRF token, JWT…" aria-label="Search labs" />
          <Select value={topic} onChange={(e) => setTopic(e.target.value)} aria-label="Topic">
            <option value="">All topics</option>
            {(library.data?.topics ?? []).map((t) => (
              <option key={t.name} value={t.name}>
                {t.name} ({t.labs.length})
              </option>
            ))}
          </Select>
        </div>
        <ErrorText error={library.error} />
        {library.isPending ? (
          <Spinner />
        ) : topics.length === 0 ? (
          <EmptyState>No labs match your search.</EmptyState>
        ) : (
          <div className="space-y-2">
            {topics.map((t) => (
              <details key={t.name} open={Boolean(query || topic)} className="group rounded-lg border border-line bg-panel">
                <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-semibold text-white">
                  {t.name}
                  <span className="text-xs font-normal text-muted">
                    {t.labs.length} lab{t.labs.length === 1 ? "" : "s"} <span className="ml-1 inline-block transition group-open:rotate-90">›</span>
                  </span>
                </summary>
                <ol className="divide-y divide-line border-t border-line">
                  {t.labs.map((l) => (
                    <li key={l.url} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
                      <span>{l.title}</span>
                      <a href={l.url} target="_blank" rel="noopener noreferrer" className="shrink-0 font-semibold text-accent hover:underline">
                        Open lab ↗
                      </a>
                    </li>
                  ))}
                </ol>
              </details>
            ))}
          </div>
        )}
        {library.data && <p className="mt-4 text-xs text-muted">{library.data.source}</p>}
      </Card>
    </>
  );
}
