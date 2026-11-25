"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { WebAttempt } from "@/lib/types";
import { formatClock, useSecondsLeft } from "@/components/countdown";
import { Button, ButtonLink, Card, ErrorText, Notice, PageHeader, Spinner } from "@/components/ui";

const CURRENT = ["web-exam-current"];

export default function ExamPage() {
  const quizId = useParams<{ quizId: string }>().quizId;
  const qc = useQueryClient();
  const exams = useQuery({ queryKey: ["web-exams"], queryFn: api.webExams });
  const current = useQuery({
    queryKey: CURRENT,
    queryFn: api.currentExam,
    // While an exam is open, keep checking: the server decides when time is over and when the instructor unlocks.
    refetchInterval: (q) => (q.state.data ? 10_000 : false),
  });
  const setAttempt = (a: WebAttempt) => qc.setQueryData(CURRENT, a);

  const start = useMutation({ mutationFn: () => api.startExam(quizId), onSuccess: setAttempt });
  const mark = useMutation({
    mutationFn: (v: { attempt: number; index: number; solved: boolean }) => api.markLab(v.attempt, v.index, v.solved),
    onSuccess: setAttempt,
    onError: () => qc.invalidateQueries({ queryKey: CURRENT }),
  });
  const finish = useMutation({ mutationFn: (id: number) => api.finishExam(id), onSuccess: setAttempt });

  const attempt = current.data;
  // Count down from the server's "seconds left", so a wrong clock on this computer does not matter.
  const endsAt = attempt?.status === "active" ? current.dataUpdatedAt + attempt.seconds_left * 1000 : null;
  const left = useSecondsLeft(endsAt);
  useEffect(() => {
    if (left === 0) qc.invalidateQueries({ queryKey: CURRENT });
  }, [left, qc]);

  const exam = exams.data?.find((q) => q.id === quizId);
  if (exams.isPending || current.isPending) return <Spinner />;
  if (exams.error || current.error) return <ErrorText error={exams.error ?? current.error} />;
  if (!exam) return <Notice tone="bad">This exam does not exist.</Notice>;

  if (attempt && attempt.quiz_id !== quizId) {
    return (
      <>
        <PageHeader title={exam.title} />
        <Notice tone="warn">
          You have another exam open ({attempt.quiz_title}). {attempt.status === "locked" ? "Ask the instructor to unlock it first." : "Finish it first."}
        </Notice>
        <div className="mt-4">
          <ButtonLink href={`/web-labs/exam/${attempt.quiz_id}`}>Go to {attempt.quiz_title}</ButtonLink>
        </div>
      </>
    );
  }

  if (attempt?.status === "locked") {
    const finishedEarly = Date.parse(attempt.ends_at) - Date.parse(attempt.started_at) < exam.duration_minutes * 60_000 - 1000;
    return (
      <div className="fixed inset-0 z-[60] flex select-none flex-col items-center justify-center bg-[#0a0a0a] px-6 text-center">
        <span className="text-7xl" aria-hidden>
          🔒
        </span>
        <h1 className="mt-4 text-4xl font-extrabold text-bad">{finishedEarly ? "EXAM SUBMITTED" : "TIME EXPIRED"}</h1>
        <p className="mt-3 text-lg text-[#bbbbbb]">This station is now locked.</p>
        <p className="mt-1 text-sm text-[#999]">
          {attempt.quiz_title}: you marked {attempt.solved_count} of {attempt.labs.length} labs as solved.
        </p>
        <p className="mt-10 animate-pulse text-sm text-[#777]">Awaiting instructor authorization…</p>
      </div>
    );
  }

  if (!attempt) {
    return (
      <div className="mx-auto max-w-2xl">
        <PageHeader title={`${exam.title}: Instructions`} subtitle={exam.description} />
        <Card>
          <ul className="list-disc space-y-2 pl-5 text-sm">
            <li>
              Time limit: <strong className="text-white">{exam.duration_minutes} minutes</strong>.
            </li>
            <li>
              You will be assigned <strong className="text-white">{exam.labs_per_attempt} random labs</strong> out of {exam.pool_size}.
            </li>
            {exam.rules.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <ErrorText error={start.error} />
          <Button
            className="mt-6 w-full bg-ok py-3 text-base text-[#04210f]"
            busy={start.isPending}
            onClick={() => {
              document.documentElement.requestFullscreen?.().catch(() => {});
              start.mutate();
            }}
          >
            START EXAM
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 rounded-lg border border-warn/40 bg-warn/10 px-4 py-2 text-center text-sm text-warn">
        ⚠️ Session active: you cannot restart until the time is over.
      </div>
      <div className="mb-6 text-center">
        <p className="text-sm text-muted">{attempt.quiz_title}</p>
        <p className={`mt-1 inline-block rounded-xl px-6 py-2 font-mono text-5xl font-bold ${left !== null && left < 60 ? "bg-bad/15 text-bad" : "bg-bad/10 text-bad"}`}>
          {formatClock(left ?? attempt.seconds_left)}
        </p>
      </div>
      <Notice tone="warn">
        <strong>Exam rule:</strong> do not scroll up to the Solution section on PortSwigger. Opening it results in a 0.
      </Notice>

      <h2 className="mb-3 mt-6 text-lg font-semibold text-accent">Your Assigned Labs</h2>
      <div className="space-y-3">
        {attempt.labs.map((lab) => (
          <div key={lab.index} className={`rounded-lg border-l-4 bg-card p-4 ${lab.solved ? "border-ok" : "border-accent"}`}>
            <p className="text-sm">
              <span className="font-semibold text-white">Lab {lab.index + 1}:</span> {lab.title}
            </p>
            <div className="mt-3 flex flex-wrap gap-3">
              <a href={lab.url} target="_blank" rel="noopener noreferrer" className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-accent-ink hover:brightness-110">
                Open Lab Activity ↗
              </a>
              <Button
                variant={lab.solved ? "primary" : "secondary"}
                className={lab.solved ? "bg-ok text-[#04210f]" : ""}
                busy={mark.isPending && mark.variables?.index === lab.index}
                onClick={() => mark.mutate({ attempt: attempt.id, index: lab.index, solved: !lab.solved })}
              >
                {lab.solved ? "Solved ✓" : "Mark as solved"}
              </Button>
            </div>
          </div>
        ))}
      </div>
      <ErrorText error={mark.error ?? finish.error} />

      <div className="mt-6 flex items-center justify-between gap-3 border-t border-line pt-4">
        <p className="text-sm text-muted">
          Marked solved: {attempt.solved_count} of {attempt.labs.length}
        </p>
        <Button
          variant="danger"
          busy={finish.isPending}
          onClick={() => {
            if (window.confirm("Finish the exam now? The station locks and you cannot change your answers.")) finish.mutate(attempt.id);
          }}
        >
          Finish Exam
        </Button>
      </div>
    </div>
  );
}
