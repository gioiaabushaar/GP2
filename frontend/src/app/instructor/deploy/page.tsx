"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { LAB_MEMORY_MB, MAX_LABS, deployments } from "@/lib/deployments";
import { Badge, Button, Card, Field, Input, Notice, PageHeader, Select, Table } from "@/components/ui";

const COURSES = ["Network Security Basics", "Web Application Security", "Cryptography Fundamentals", "Digital Forensics"];

type Line = { text: string; tone?: "ok" | "bad" };

export default function DeployLabs() {
  const challenges = useQuery({ queryKey: ["challenges", {}], queryFn: () => api.challenges() });
  const [course, setCourse] = useState(COURSES[0]);
  const [moduleName, setModuleName] = useState("");
  const [students, setStudents] = useState(30);
  const [lines, setLines] = useState<Line[]>([{ text: "> Waiting for instruction..." }]);
  const [running, setRunning] = useState(false);
  const [provisioned, setProvisioned] = useState(0);
  const timers = useRef<number[]>([]);

  useEffect(() => () => timers.current.forEach((t) => window.clearTimeout(t)), []);

  const labModule = moduleName || challenges.data?.[0]?.title || "";

  function deploy() {
    timers.current.forEach((t) => window.clearTimeout(t));
    setProvisioned(0);
    const id = String(Date.now());
    const at = new Date().toISOString();
    const head: Line = { text: `> Deployment request: ${students} students, module "${labModule}", course "${course}"` };

    if (students > MAX_LABS) {
      setLines([
        head,
        { text: `> Capacity check: ${students} labs x ${LAB_MEMORY_MB} MB needs ${((students * LAB_MEMORY_MB) / 1024).toFixed(1)} GB` },
        { text: `> Refused: this host can run at most ${MAX_LABS} labs at once. Deploy in smaller groups.`, tone: "bad" },
      ]);
      deployments.add({ id, course, module: labModule, students, at, status: "Refused" });
      return;
    }

    const steps: Line[] = [
      { text: `> Capacity check passed (${students} of ${MAX_LABS} labs)` },
      { text: `> Pulling lab image for "${labModule}"...` },
      { text: `> Creating ${students} isolated student networks...` },
      { text: `> Applying resource quotas (0.5 CPU, ${LAB_MEMORY_MB} MB)...` },
      { text: "> Starting containers..." },
      { text: "> Verifying health checks..." },
      { text: "> Infrastructure deployed successfully.", tone: "ok" },
    ];
    setRunning(true);
    setLines([head]);
    steps.forEach((step, i) => {
      timers.current.push(
        window.setTimeout(() => {
          setLines((l) => [...l, step]);
          if (i === steps.length - 1) {
            setRunning(false);
            setProvisioned(students);
            deployments.add({ id, course, module: labModule, students, at, status: "Running" });
          }
        }, (i + 1) * 600),
      );
    });
  }

  const rows = Array.from({ length: Math.min(provisioned, 8) }, (_, i) => String(i + 1).padStart(2, "0"));

  return (
    <>
      <PageHeader
        title="One-Click Infrastructure Deployment"
        subtitle="Prepare a lab module for a whole class in one step."
        actions={<Badge tone="warn">Simulated until the lab manager deploy API (FR6) exists</Badge>}
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Configuration">
          <div className="space-y-4">
            <Field label="Course Selection">
              <Select value={course} onChange={(e) => setCourse(e.target.value)}>
                {COURSES.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </Select>
            </Field>
            <Field label="Target Lab Module">
              <Select value={labModule} onChange={(e) => setModuleName(e.target.value)}>
                {(challenges.data ?? []).map((c) => (
                  <option key={c.id}>{c.title}</option>
                ))}
              </Select>
            </Field>
            <Field label="Number of Students" hint={`This host fits up to ${MAX_LABS} labs at ${LAB_MEMORY_MB} MB each.`}>
              <Input type="number" min={1} max={5000} value={students} onChange={(e) => setStudents(Math.max(1, Number(e.target.value) || 1))} />
            </Field>
            <Button onClick={deploy} busy={running} disabled={!labModule}>
              Deploy Infrastructure
            </Button>
          </div>
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

      {provisioned > 0 && (
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
          {provisioned > rows.length && <p className="mt-3 text-sm text-muted">… and {provisioned - rows.length} more containers.</p>}
        </Card>
      )}

      <div className="mt-4">
        <Notice tone="info">
          Nothing is started on the server from this page yet. It shows the planned flow, including the capacity check that refuses
          deployments the host cannot fit.
        </Notice>
      </div>
    </>
  );
}
