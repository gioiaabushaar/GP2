"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { CATEGORIES, DIFFICULTIES } from "@/lib/types";
import { Badge, Button, Card, ErrorText, Field, Input, Notice, PageHeader, Select, Spinner, Table, Textarea, difficultyTone } from "@/components/ui";

const EMPTY = { title: "", category: "Web", difficulty: "Easy", points: "", flag: "", description: "", writeup: "" };

export default function ManageChallenges() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["challenges", {}], queryFn: () => api.challenges() });
  const [form, setForm] = useState(EMPTY);
  const [saved, setSaved] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      api.createChallenge({
        title: form.title,
        category: form.category,
        difficulty: form.difficulty,
        points: form.points ? Number(form.points) : null,
        flag: form.flag.trim(),
        description: form.description,
        writeup: form.writeup,
      }),
    onSuccess: (c) => {
      setSaved(`Saved "${c.title}" (${c.points} points). Students can see it now.`);
      setForm(EMPTY);
      qc.invalidateQueries({ queryKey: ["challenges"] });
      qc.invalidateQueries({ queryKey: ["overview"] });
    },
  });

  const set = (key: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setSaved(null);
    setForm({ ...form, [key]: e.target.value });
  };

  return (
    <>
      <PageHeader title="Content Management" subtitle="Create platform challenges. Flags are stored hashed and never shown again." />
      <div className="grid gap-4 xl:grid-cols-2">
        <Card title="New Challenge">
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate();
            }}
          >
            <Field label="Challenge Title">
              <Input required minLength={3} maxLength={150} value={form.title} onChange={set("title")} placeholder="e.g. SSRF Evasion" />
            </Field>
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Category">
                <Select value={form.category} onChange={set("category")}>
                  {CATEGORIES.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </Select>
              </Field>
              <Field label="Difficulty">
                <Select value={form.difficulty} onChange={set("difficulty")}>
                  {DIFFICULTIES.map((d) => (
                    <option key={d}>{d}</option>
                  ))}
                </Select>
              </Field>
              <Field label="Points" hint="Empty: 100 / 200 / 300">
                <Input type="number" min={10} max={2000} value={form.points} onChange={set("points")} />
              </Field>
            </div>
            <Field label="Expected Flag" hint="Format: NEXIS{...} with no spaces.">
              <Input required pattern="NEXIS\{[^\{\}\s]{3,200}\}" value={form.flag} onChange={set("flag")} placeholder="NEXIS{...}" className="font-mono" />
            </Field>
            <Field label="Description (shown to students)">
              <Textarea required minLength={10} value={form.description} onChange={set("description")} />
            </Field>
            <Field label="Reference write-up (for the AI mentor, never shown to students)">
              <Textarea required minLength={20} value={form.writeup} onChange={set("writeup")} />
            </Field>
            <ErrorText error={create.error} />
            {saved && <Notice tone="ok">{saved}</Notice>}
            <Button type="submit" busy={create.isPending}>
              Save Challenge
            </Button>
          </form>
        </Card>

        <Card title="Published Challenges">
          {list.isPending ? (
            <Spinner />
          ) : (
            <Table head={["Title", "Category", "Difficulty", "Points"]}>
              {(list.data ?? []).map((c) => (
                <tr key={c.id}>
                  <td className="px-3 py-2 text-white">{c.title}</td>
                  <td className="px-3 py-2">{c.category}</td>
                  <td className="px-3 py-2">
                    <Badge tone={difficultyTone(c.difficulty)}>{c.difficulty}</Badge>
                  </td>
                  <td className="px-3 py-2">{c.points}</td>
                </tr>
              ))}
            </Table>
          )}
          <ErrorText error={list.error} />
        </Card>
      </div>
    </>
  );
}
