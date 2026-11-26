"use client";

import { useDeferredValue, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { WebExam, WebExamInput } from "@/lib/types";
import { Badge, Button, Card, EmptyState, ErrorText, Field, Input, Notice, Spinner, Textarea } from "../ui";

const BLANK: WebExamInput = { title: "", description: "", duration_minutes: 7, labs_per_attempt: 3, rules: "", active: true };

const toInput = (e: WebExam): WebExamInput => ({
  title: e.title,
  description: e.description,
  duration_minutes: e.duration_minutes,
  labs_per_attempt: e.labs_per_attempt,
  rules: e.rules.join("\n"),
  active: e.active,
});

/** Exam setup: create, edit, hide and delete exams, and manage each exam's lab pool. */
export function ExamManager() {
  const qc = useQueryClient();
  const exams = useQuery({ queryKey: ["web-exams"], queryFn: api.webExams });
  const [selected, setSelected] = useState<string | null>(null);
  const [form, setForm] = useState<{ mode: "new" | "edit"; data: WebExamInput } | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: ["web-exams"] });

  const save = useMutation({
    mutationFn: (f: { mode: "new" | "edit"; data: WebExamInput }) =>
      f.mode === "new" ? api.createExam(f.data) : api.updateExam(selected!, f.data),
    onSuccess: (exam) => {
      setForm(null);
      setSelected(exam.id);
      refresh();
    },
  });
  const toggle = useMutation({ mutationFn: (e: WebExam) => api.updateExam(e.id, { active: !e.active }), onSuccess: refresh });
  const remove = useMutation({
    mutationFn: (id: string) => api.deleteExam(id),
    onSuccess: () => {
      setSelected(null);
      refresh();
    },
  });

  const exam = exams.data?.find((e) => e.id === selected);

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <Card
        title="Exams"
        actions={
          <Button className="px-3 py-1" onClick={() => setForm({ mode: "new", data: BLANK })}>
            New exam
          </Button>
        }
      >
        {exams.isPending ? (
          <Spinner />
        ) : (
          <ul className="space-y-2">
            {(exams.data ?? []).map((e) => (
              <li key={e.id}>
                <button
                  onClick={() => {
                    setSelected(e.id);
                    setForm(null);
                  }}
                  className={`w-full rounded-lg border px-4 py-3 text-left transition ${
                    e.id === selected ? "border-accent bg-accent/5" : "border-line bg-panel hover:border-accent/50"
                  }`}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-white">{e.title}</span>
                    {e.active ? <Badge tone="ok">Visible</Badge> : <Badge tone="muted">Hidden</Badge>}
                  </span>
                  <span className="mt-1 block text-xs text-muted">
                    {e.duration_minutes} min · {e.labs_per_attempt} labs per attempt · pool of {e.pool_size}
                  </span>
                  {e.pool_size < e.labs_per_attempt && <span className="mt-1 block text-xs text-warn">Needs more labs before students can start</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
        <ErrorText error={exams.error ?? toggle.error ?? remove.error} />
      </Card>

      <div className="min-w-0 space-y-4">
        {form ? (
          <ExamForm
            key={form.mode + (selected ?? "")}
            initial={form.data}
            heading={form.mode === "new" ? "New exam" : `Edit ${exam?.title}`}
            busy={save.isPending}
            error={save.error}
            onCancel={() => setForm(null)}
            onSave={(data) => save.mutate({ mode: form.mode, data })}
          />
        ) : exam ? (
          <>
            <Card
              title={exam.title}
              actions={
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" className="px-3 py-1" onClick={() => setForm({ mode: "edit", data: toInput(exam) })}>
                    Edit
                  </Button>
                  <Button variant="secondary" className="px-3 py-1" busy={toggle.isPending} onClick={() => toggle.mutate(exam)}>
                    {exam.active ? "Hide from students" : "Show to students"}
                  </Button>
                  <Button
                    variant="dangerGhost"
                    className="px-3 py-1"
                    onClick={() => {
                      if (window.confirm(`Delete "${exam.title}"? This cannot be undone.`)) remove.mutate(exam.id);
                    }}
                  >
                    Delete
                  </Button>
                </div>
              }
            >
              {exam.description && <p className="text-sm text-muted">{exam.description}</p>}
              <p className="mt-2 text-sm">
                <span className="text-accent">{exam.duration_minutes} minutes</span> · {exam.labs_per_attempt} random labs per attempt
              </p>
              {exam.rules.length > 0 && (
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
                  {exam.rules.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              )}
            </Card>
            <PoolEditor exam={exam} />
          </>
        ) : (
          <EmptyState>Select an exam to see its labs, or create a new one.</EmptyState>
        )}
      </div>
    </div>
  );
}

function ExamForm(props: {
  initial: WebExamInput;
  heading: string;
  busy: boolean;
  error: unknown;
  onCancel: () => void;
  onSave: (data: WebExamInput) => void;
}) {
  const [data, setData] = useState(props.initial);
  const set = <K extends keyof WebExamInput>(key: K, value: WebExamInput[K]) => setData({ ...data, [key]: value });

  return (
    <Card title={props.heading}>
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          props.onSave(data);
        }}
      >
        <Field label="Title">
          <Input required minLength={2} maxLength={120} value={data.title} onChange={(e) => set("title", e.target.value)} placeholder="e.g. Quiz 4" />
        </Field>
        <Field label="Description (shown to students)">
          <Input maxLength={2000} value={data.description} onChange={(e) => set("description", e.target.value)} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Time limit (minutes)">
            <Input type="number" required min={1} max={240} value={data.duration_minutes} onChange={(e) => set("duration_minutes", Number(e.target.value))} />
          </Field>
          <Field label="Labs per attempt">
            <Input type="number" required min={1} max={20} value={data.labs_per_attempt} onChange={(e) => set("labs_per_attempt", Number(e.target.value))} />
          </Field>
        </div>
        <Field label="Rules (one per line, shown before the exam starts)">
          <Textarea maxLength={4000} value={data.rules} onChange={(e) => set("rules", e.target.value)} />
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={data.active} onChange={(e) => set("active", e.target.checked)} className="h-4 w-4 accent-[var(--accent)]" />
          Visible to students
        </label>
        <ErrorText error={props.error} />
        <div className="flex gap-3">
          <Button type="submit" busy={props.busy}>
            Save exam
          </Button>
          <Button type="button" variant="ghost" onClick={props.onCancel}>
            Cancel
          </Button>
        </div>
        <p className="text-xs text-muted">Changes apply to new attempts. Exams already running keep their labs and end time.</p>
      </form>
    </Card>
  );
}

function PoolEditor({ exam }: { exam: WebExam }) {
  const qc = useQueryClient();
  const library = useQuery({ queryKey: ["web-library"], queryFn: api.webLibrary });
  const [search, setSearch] = useState("");
  const [custom, setCustom] = useState({ title: "", url: "" });
  const query = useDeferredValue(search.trim().toLowerCase());
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["web-exams"] });
  };
  const add = useMutation({ mutationFn: (lab: { title: string; url: string }) => api.addExamLab(exam.id, lab), onSuccess: refresh });
  const remove = useMutation({ mutationFn: (labId: number) => api.removeExamLab(exam.id, labId), onSuccess: refresh });

  const inPool = new Set((exam.pool ?? []).map((l) => l.url));
  const matches = query
    ? (library.data?.topics ?? []).flatMap((t) => t.labs.map((l) => ({ ...l, topic: t.name }))).filter((l) => !inPool.has(l.url) && `${l.title} ${l.topic}`.toLowerCase().includes(query)).slice(0, 8)
    : [];

  return (
    <Card title={`Lab pool (${exam.pool_size})`}>
      {exam.pool_size < exam.labs_per_attempt && (
        <div className="mb-3">
          <Notice tone="warn">
            Each attempt draws {exam.labs_per_attempt} labs, so the pool needs at least {exam.labs_per_attempt}. Students cannot start this exam yet.
          </Notice>
        </div>
      )}
      {(exam.pool ?? []).length === 0 ? (
        <EmptyState>No labs yet. Add some from the library or by link below.</EmptyState>
      ) : (
        <ol className="divide-y divide-line rounded-lg border border-line">
          {(exam.pool ?? []).map((l, i) => (
            <li key={l.id} className="flex items-center gap-3 px-3 py-2 text-sm">
              <span className="w-6 text-muted">{i + 1}.</span>
              <a href={l.url} target="_blank" rel="noopener noreferrer" className="flex-1 hover:text-accent hover:underline">
                {l.title}
              </a>
              <Button variant="dangerGhost" className="px-2 py-1" busy={remove.isPending && remove.variables === l.id} onClick={() => remove.mutate(l.id)}>
                Remove
              </Button>
            </li>
          ))}
        </ol>
      )}

      <h3 className="mb-2 mt-5 text-sm font-semibold text-white">Add from the library</h3>
      <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search library labs, e.g. CSRF token" aria-label="Search library labs" />
      {matches.length > 0 && (
        <ul className="mt-2 divide-y divide-line rounded-lg border border-line">
          {matches.map((l) => (
            <li key={l.id} className="flex items-center gap-3 px-3 py-2 text-sm">
              <span className="flex-1">
                {l.title} <span className="text-xs text-muted">· {l.topic}</span>
              </span>
              <Button variant="secondary" className="px-3 py-1" busy={add.isPending && add.variables?.url === l.url} onClick={() => add.mutate({ title: l.title, url: l.url })}>
                Add
              </Button>
            </li>
          ))}
        </ul>
      )}
      {query && matches.length === 0 && !library.isPending && <p className="mt-2 text-xs text-muted">No library labs match (or they are already in this exam).</p>}

      <h3 className="mb-2 mt-5 text-sm font-semibold text-white">Or add by link</h3>
      <form
        className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]"
        onSubmit={(e) => {
          e.preventDefault();
          add.mutate(custom, { onSuccess: () => setCustom({ title: "", url: "" }) });
        }}
      >
        <Input required maxLength={300} value={custom.title} onChange={(e) => setCustom({ ...custom, title: e.target.value })} placeholder="Title, e.g. Burp Suite: Intruder basics" aria-label="Lab title" />
        <Input required type="url" maxLength={500} value={custom.url} onChange={(e) => setCustom({ ...custom, url: e.target.value })} placeholder="https://…" aria-label="Lab link" />
        <Button type="submit" variant="secondary" busy={add.isPending && add.variables?.url === custom.url}>
          Add
        </Button>
      </form>
      <div className="mt-2">
        <ErrorText error={add.error ?? remove.error} />
      </div>
    </Card>
  );
}
