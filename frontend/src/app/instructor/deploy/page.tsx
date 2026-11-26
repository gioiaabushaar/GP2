"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/insights";
import type { Course, Deployment } from "@/lib/types";
import { Badge, Button, Card, EmptyState, ErrorText, Field, Input, Notice, PageHeader, Select, Spinner, Table } from "@/components/ui";

type Line = { text: string; tone?: "ok" | "bad" };

export default function DeployLabs() {
  const qc = useQueryClient();
  const challenges = useQuery({ queryKey: ["challenges", {}], queryFn: () => api.challenges() });
  const courses = useQuery({ queryKey: ["courses"], queryFn: api.courses });
  const capacity = useQuery({ queryKey: ["capacity"], queryFn: api.capacity });
  const history = useQuery({ queryKey: ["deployments"], queryFn: api.deployments });

  const [courseId, setCourseId] = useState<number | null>(null);
  const [challengeId, setChallengeId] = useState<number | null>(null);
  const [students, setStudents] = useState(30);
  const [lines, setLines] = useState<Line[]>([{ text: "> Waiting for instruction..." }]);
  const [shown, setShown] = useState<Deployment | null>(null);
  const timers = useRef<number[]>([]);
  useEffect(() => () => timers.current.forEach((t) => window.clearTimeout(t)), []);

  const course = courses.data?.find((c) => c.id === courseId) ?? courses.data?.[0];
  const challenge = challenges.data?.find((c) => c.id === challengeId) ?? challenges.data?.[0];
  const cap = capacity.data;

  const deploy = useMutation({
    mutationFn: () => api.deploy({ course_id: course!.id, challenge_id: challenge!.id, students }),
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ["deployments"] });
      animate(d);
    },
  });

  // The log replays the deployment steps; the server has already decided and recorded the result.
  function animate(d: Deployment) {
    timers.current.forEach((t) => window.clearTimeout(t));
    setShown(null);
    const head: Line = { text: `> Deployment request: ${d.students} students, module "${d.challenge_title}", course "${d.course_name}"` };
    if (d.status === "refused") {
      setLines([head, { text: `> Refused: ${d.reason}`, tone: "bad" }]);
      return;
    }
    const steps: Line[] = [
      { text: `> Capacity check passed (${d.students} of ${cap?.max_labs ?? "?"} labs)` },
      { text: `> Pulling lab image for "${d.challenge_title}"...` },
      { text: `> Creating ${d.students} isolated student networks...` },
      { text: `> Applying resource quotas (0.5 CPU, ${cap?.lab_memory_mb ?? 256} MB)...` },
      { text: "> Starting containers..." },
      { text: "> Verifying health checks..." },
      { text: "> Infrastructure deployed successfully.", tone: "ok" },
    ];
    setLines([head]);
    steps.forEach((step, i) => {
      timers.current.push(
        window.setTimeout(() => {
          setLines((l) => [...l, step]);
          if (i === steps.length - 1) setShown(d);
        }, (i + 1) * 600),
      );
    });
  }

  const rows = shown ? Array.from({ length: Math.min(shown.students, 8) }, (_, i) => String(i + 1).padStart(2, "0")) : [];

  return (
    <>
      <PageHeader
        title="One-Click Infrastructure Deployment"
        subtitle="Prepare a lab module for a whole class in one step."
        actions={<Badge tone="warn">Simulated until the lab manager deploy API (FR6) exists</Badge>}
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Configuration">
          {courses.isPending || challenges.isPending ? (
            <Spinner />
          ) : (
            <div className="space-y-4">
              <Field label="Course Selection">
                <Select value={course?.id ?? ""} onChange={(e) => setCourseId(Number(e.target.value))}>
                  {(courses.data ?? []).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Target Lab Module">
                <Select value={challenge?.id ?? ""} onChange={(e) => setChallengeId(Number(e.target.value))}>
                  {(challenges.data ?? []).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.title}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Number of Students" hint={cap ? `This host fits up to ${cap.max_labs} labs at ${cap.lab_memory_mb} MB each.` : undefined}>
                <Input type="number" min={1} max={5000} value={students} onChange={(e) => setStudents(Math.max(1, Number(e.target.value) || 1))} />
              </Field>
              <ErrorText error={deploy.error ?? courses.error ?? capacity.error} />
              <Button onClick={() => deploy.mutate()} busy={deploy.isPending} disabled={!course || !challenge}>
                Deploy Infrastructure
              </Button>
            </div>
          )}
        </Card>

        <div className="overflow-hidden rounded-xl border border-line bg-black">
          <div className="border-b border-white/10 bg-[#2a2f3a] px-4 py-2 font-mono text-xs text-[#c9d1d9]">Docker Deployment Daemon Logs</div>
          <div className="h-72 overflow-y-auto p-4 font-mono text-[13px]" aria-live="polite">
            {lines.map((l, i) => (
              <p key={i} className={l.tone === "bad" ? "text-bad" : l.tone === "ok" ? "text-ok" : "text-[#4ade80]"}>
                {l.text}
              </p>
            ))}
          </div>
        </div>
      </div>

      {shown && (
        <Card title="Provisioned Containers" className="mt-4">
          <Table head={["Container ID", "Status", "URL", "Network"]}>
            {rows.map((n) => (
              <tr key={n}>
                <td className="px-3 py-2 font-mono">nex-stu-{n}</td>
                <td className="px-3 py-2 text-ok">Running</td>
                <td className="px-3 py-2 font-mono">http://lab-{n}.local</td>
                <td className="px-3 py-2">Isolated-{n}</td>
              </tr>
            ))}
          </Table>
          {shown.students > rows.length && <p className="mt-3 text-sm text-muted">… and {shown.students - rows.length} more containers.</p>}
        </Card>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Deployment History">
          {history.isPending ? (
            <Spinner />
          ) : !history.data?.length ? (
            <EmptyState>No deployments yet.</EmptyState>
          ) : (
            <Table head={["When", "Course", "Module", "Students", "Status"]}>
              {history.data.slice(0, 10).map((d) => (
                <tr key={d.id}>
                  <td className="whitespace-nowrap px-3 py-2 text-xs text-muted">{formatDate(d.created_at)}</td>
                  <td className="px-3 py-2">{d.course_name}</td>
                  <td className="px-3 py-2">{d.challenge_title}</td>
                  <td className="px-3 py-2">{d.students}</td>
                  <td className={`px-3 py-2 ${d.status === "running" ? "text-ok" : "text-bad"}`}>{d.status === "running" ? "Running" : "Refused"}</td>
                </tr>
              ))}
            </Table>
          )}
          <ErrorText error={history.error} />
        </Card>
        <CourseManager courses={courses.data ?? []} />
      </div>

      <div className="mt-4">
        <Notice tone="info">
          Nothing is started on the server from this page yet. Courses, the capacity check and the deployment history are real and
          stored in the database.
        </Notice>
      </div>
    </>
  );
}

function CourseManager({ courses }: { courses: Course[] }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<{ id: number; name: string } | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: ["courses"] });
  const add = useMutation({
    mutationFn: () => api.addCourse(name),
    onSuccess: () => {
      setName("");
      refresh();
    },
  });
  const rename = useMutation({
    mutationFn: (c: { id: number; name: string }) => api.renameCourse(c.id, c.name),
    onSuccess: () => {
      setEditing(null);
      refresh();
    },
  });
  const remove = useMutation({ mutationFn: (id: number) => api.deleteCourse(id), onSuccess: refresh });

  return (
    <Card title="Courses">
      <ul className="divide-y divide-line">
        {courses.map((c) => (
          <li key={c.id} className="flex items-center gap-2 py-2 text-sm">
            {editing?.id === c.id ? (
              <form
                className="flex flex-1 gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  rename.mutate(editing);
                }}
              >
                <Input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} aria-label="Course name" autoFocus />
                <Button type="submit" className="px-3 py-1" busy={rename.isPending}>
                  Save
                </Button>
                <Button type="button" variant="ghost" className="px-2 py-1" onClick={() => setEditing(null)}>
                  Cancel
                </Button>
              </form>
            ) : (
              <>
                <span className="flex-1 text-white">{c.name}</span>
                <Button variant="ghost" className="px-2 py-1" onClick={() => setEditing({ id: c.id, name: c.name })}>
                  Rename
                </Button>
                <Button
                  variant="dangerGhost"
                  className="px-2 py-1"
                  onClick={() => {
                    if (window.confirm(`Delete the course "${c.name}"? Past deployments keep its name.`)) remove.mutate(c.id);
                  }}
                >
                  Delete
                </Button>
              </>
            )}
          </li>
        ))}
      </ul>
      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim().length >= 2) add.mutate();
        }}
      >
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="New course name" aria-label="New course name" minLength={2} maxLength={120} />
        <Button type="submit" variant="secondary" busy={add.isPending} disabled={name.trim().length < 2}>
          Add
        </Button>
      </form>
      <div className="mt-2">
        <ErrorText error={add.error ?? rename.error ?? remove.error} />
      </div>
    </Card>
  );
}
