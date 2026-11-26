"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "@/lib/api";
import { learningPattern, parseServerDate } from "@/lib/insights";
import type { LabSession, SubmitResult } from "@/lib/types";
import { Countdown, formatClock, useElapsedSeconds } from "@/components/countdown";
import { MentorChat } from "@/components/mentor-chat";
import { Badge, Button, ButtonLink, Card, ErrorText, Input, Modal, Notice, Spinner, difficultyTone } from "@/components/ui";

export default function ActiveLab() {
  const id = Number(useParams<{ id: string }>().id);
  const qc = useQueryClient();
  const elapsed = useElapsedSeconds();

  const challenge = useQuery({ queryKey: ["challenge", id], queryFn: () => api.challenge(id), enabled: Number.isInteger(id) });
  const labs = useQuery({ queryKey: ["my-labs"], queryFn: api.myLabs });
  // The report endpoint is the per-challenge source of attempts and hints; 404 just means "no activity yet".
  const stats = useQuery({
    queryKey: ["report", id],
    queryFn: () => api.report(id).catch((e) => (e instanceof ApiError && e.status === 404 ? null : Promise.reject(e))),
  });

  const running = labs.data?.find((l) => l.status === "running");
  const mine = running?.challenge_id === id ? running : undefined;
  const otherRunning = running && running.challenge_id !== id ? running : undefined;

  const refresh = () => qc.invalidateQueries({ queryKey: ["my-labs"] });
  const start = useMutation({ mutationFn: () => api.startLab(id), onSuccess: refresh });
  const stop = useMutation({ mutationFn: (s: LabSession) => api.stopLab(s.id), onSuccess: refresh });
  const restart = useMutation({
    mutationFn: async (s: LabSession) => {
      await api.stopLab(s.id);
      return api.startLab(id);
    },
    onSuccess: refresh,
  });

  const [result, setResult] = useState<SubmitResult | null>(null);
  const [flag, setFlag] = useState("");
  const [celebrate, setCelebrate] = useState(false);
  const submit = useMutation({
    mutationFn: () => api.submitFlag(id, flag),
    onSuccess: (res) => {
      setResult(res);
      if (res.correct) setFlag("");
      if (res.correct && !res.already_solved) setCelebrate(true);
      qc.invalidateQueries({ queryKey: ["report", id] });
      qc.invalidateQueries({ queryKey: ["my-score"] });
      qc.invalidateQueries({ queryKey: ["my-activity"] });
      qc.invalidateQueries({ queryKey: ["challenges"] });
    },
  });
  if (!Number.isInteger(id)) return <Notice tone="bad">This challenge address is not valid.</Notice>;
  if (challenge.isPending) return <Spinner />;
  if (challenge.error) return <ErrorText error={challenge.error} />;
  const c = challenge.data;

  // The server says when the lab is removed (start time + the lab lifetime it is configured with).
  const endsAt = mine ? parseServerDate(mine.expires_at).getTime() : null;
  const labError = start.error ?? stop.error ?? restart.error;
  const dockerOff = labError instanceof ApiError && labError.status === 503;

  const attempts = stats.data?.attempts ?? 0;
  const hints = stats.data?.hints_used ?? 0;
  const solved = Boolean(stats.data?.solved || c.solved);
  const pattern = learningPattern({ solved, attempts, hints });

  return (
    <>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{c.title}</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge tone={difficultyTone(c.difficulty)}>Difficulty: {c.difficulty}</Badge>
            <Badge tone="muted">{c.category}</Badge>
            <Badge tone="muted">{c.points} pts</Badge>
            {solved && <Badge tone="ok">Solved</Badge>}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Countdown endsAt={endsAt} />
          {mine ? (
            <>
              <Button variant="secondary" busy={restart.isPending} onClick={() => restart.mutate(mine)}>
                Restart Container
              </Button>
              <Button variant="danger" busy={stop.isPending} onClick={() => stop.mutate(mine)}>
                Stop Lab
              </Button>
            </>
          ) : (
            <Button busy={start.isPending} onClick={() => start.mutate()} disabled={Boolean(otherRunning)}>
              Launch Isolated Lab
            </Button>
          )}
        </div>
      </div>

      {otherRunning && (
        <div className="mb-4">
          <Notice tone="warn">
            You already have a lab running for another challenge. Only one lab can run at a time.{" "}
            <button className="font-semibold underline" onClick={() => stop.mutate(otherRunning)}>
              Stop that lab
            </button>
          </Notice>
        </div>
      )}
      {labError && (
        <div className="mb-4">
          {dockerOff ? (
            <Notice tone="warn">
              Lab containers are turned off on this server. You can still read the brief, ask the mentor and submit the flag. (Server
              message: {labError.message})
            </Notice>
          ) : (
            <ErrorText error={labError} />
          )}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card title="Environment Status">
            <dl className="grid gap-1 text-sm sm:grid-cols-2">
              <Row label="Status">
                {mine ? <Badge tone="ok">Running</Badge> : <Badge tone="bad">Not Running</Badge>}
              </Row>
              <Row label="Session">{mine ? `#${mine.id}` : "—"}</Row>
              <Row label="Container ID">{restart.data?.container_id ?? start.data?.container_id ?? (mine ? "shown at launch" : "—")}</Row>
              <Row label="Start time">{start.data ? `${start.data.provision_seconds}s` : "—"}</Row>
              <Row label="Network">Isolated (no network access)</Row>
              <Row label="Resources">0.5 CPU / 128 MB RAM</Row>
            </dl>
          </Card>

          <div className="overflow-hidden rounded-xl border border-line">
            <div className="flex items-center gap-2 border-b border-black/10 bg-[#e8ebf0] px-4 py-2 font-mono text-xs text-[#4b5565]">
              <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
              <span className="ml-2 truncate">nexis://challenge/{c.id}/brief</span>
            </div>
            <div className="bg-white p-6 text-[#1f2633]">
              <h2 className="text-lg font-bold">Challenge brief</h2>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">{c.description}</p>
              <p className="mt-4 text-xs text-[#6b7280]">
                The lab target opens here once the lab engine exposes a web service for this challenge.
              </p>
            </div>
          </div>

          <Card title="Submit Flag">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (flag.trim()) submit.mutate();
              }}
              className="flex flex-col gap-3 sm:flex-row"
            >
              <Input value={flag} onChange={(e) => setFlag(e.target.value)} placeholder="NEXIS{...}" aria-label="Flag" className="font-mono" />
              <Button type="submit" busy={submit.isPending} disabled={!flag.trim()}>
                Submit
              </Button>
            </form>
            <div className="mt-3 space-y-2">
              <ErrorText error={submit.error} />
              {result && !result.correct && <Notice tone="bad">Incorrect flag. Try again. (Attempt {result.attempt_number})</Notice>}
              {result?.already_solved && <Notice tone="info">{result.message}</Notice>}
              {result?.correct && !result.already_solved && (
                <Notice tone="ok">
                  Correct flag! +{result.points_awarded} points. Your total is now {result.total_score}.
                </Notice>
              )}
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card title="Behavior Analytics">
            <dl className="space-y-1 text-sm">
              <Row label="Time Spent">{formatClock(elapsed)}</Row>
              <Row label="Flag Attempts">{attempts}</Row>
              <Row label="Hints Requested">{hints}</Row>
              <Row label="Pattern">
                <span className="text-accent">{pattern}</span>
              </Row>
            </dl>
          </Card>
          <MentorChat challengeId={id} onHint={() => qc.invalidateQueries({ queryKey: ["report", id] })} />
        </div>
      </div>

      <Modal open={celebrate}>
        <h2 className="text-xl font-bold text-ok">Challenge Completed!</h2>
        <p className="mt-2 text-sm text-muted">
          You captured the flag and earned <span className="font-semibold text-white">+{result?.points_awarded} points</span>.
        </p>
        <div className="mt-5 flex justify-center gap-3">
          <ButtonLink href={`/reports/${id}`}>View AI Report</ButtonLink>
          <Button variant="secondary" onClick={() => setCelebrate(false)}>
            Close
          </Button>
        </div>
      </Modal>
    </>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <dt className="text-muted">{label}:</dt>
      <dd className="text-white">{children}</dd>
    </div>
  );
}
