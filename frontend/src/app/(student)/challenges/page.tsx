"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { CATEGORIES, DIFFICULTIES } from "@/lib/types";
import { Badge, ButtonLink, EmptyState, ErrorText, PageHeader, Select, Spinner, difficultyTone } from "@/components/ui";

export default function ChallengeLibrary() {
  const [category, setCategory] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [status, setStatus] = useState<"" | "new" | "completed">("");
  const list = useQuery({
    queryKey: ["challenges", { category, difficulty }],
    queryFn: () => api.challenges({ category, difficulty }),
  });

  const shown = (list.data ?? []).filter((c) => !status || (status === "completed" ? c.solved : !c.solved));

  return (
    <>
      <PageHeader title="Challenge Library" subtitle="Select a challenge to launch an isolated environment." />
      <div className="mb-6 grid gap-3 sm:grid-cols-3">
        <Select aria-label="Category" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </Select>
        <Select aria-label="Difficulty" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
          <option value="">All difficulties</option>
          {DIFFICULTIES.map((d) => (
            <option key={d}>{d}</option>
          ))}
        </Select>
        <Select aria-label="Status" value={status} onChange={(e) => setStatus(e.target.value as typeof status)}>
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="completed">Completed</option>
        </Select>
      </div>

      <ErrorText error={list.error} />
      {list.isPending ? (
        <Spinner />
      ) : shown.length === 0 ? (
        <EmptyState>No challenges match these filters.</EmptyState>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {shown.map((c) => (
            <article key={c.id} className="flex flex-col rounded-xl border border-line bg-card p-5">
              <h2 className="font-semibold text-white">{c.title}</h2>
              <div className="mt-2 flex flex-wrap gap-2">
                {c.solved ? <Badge tone="ok">Completed</Badge> : <Badge>New</Badge>}
                <Badge tone={difficultyTone(c.difficulty)}>{c.difficulty}</Badge>
              </div>
              <p className="mt-3 line-clamp-2 text-sm text-muted">{c.description}</p>
              <dl className="mt-3 space-y-1 text-sm">
                <div>
                  <dt className="inline text-muted">Category: </dt>
                  <dd className="inline">{c.category}</dd>
                </div>
                <div>
                  <dt className="inline text-muted">Points: </dt>
                  <dd className="inline">{c.points}</dd>
                </div>
              </dl>
              <div className="mt-auto pt-4">
                {c.solved ? (
                  <ButtonLink href={`/reports/${c.id}`} variant="secondary">
                    Review Lab
                  </ButtonLink>
                ) : (
                  <ButtonLink href={`/lab/${c.id}`}>Start Challenge</ButtonLink>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
