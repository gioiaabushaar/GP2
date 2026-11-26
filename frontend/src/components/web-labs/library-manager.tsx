"use client";

import { useDeferredValue, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { LibraryLab } from "@/lib/types";
import { Button, Card, EmptyState, ErrorText, Input, Select, Spinner } from "../ui";

const SHOW = 50;
const BLANK = { topic: "", title: "", url: "" };

/** Practice library: add, edit and delete labs (topic, title, link). */
export function LibraryManager() {
  const qc = useQueryClient();
  const library = useQuery({ queryKey: ["web-library"], queryFn: api.webLibrary });
  const [search, setSearch] = useState("");
  const [topic, setTopic] = useState("");
  const [draft, setDraft] = useState(BLANK);
  const [editing, setEditing] = useState<LibraryLab | null>(null);
  const query = useDeferredValue(search.trim().toLowerCase());
  const refresh = () => qc.invalidateQueries({ queryKey: ["web-library"] });

  const add = useMutation({
    mutationFn: () => api.addLibraryLab(draft),
    onSuccess: () => {
      setDraft({ ...BLANK, topic: draft.topic });
      refresh();
    },
  });
  const save = useMutation({
    mutationFn: (lab: LibraryLab) => api.updateLibraryLab(lab.id, { topic: lab.topic, title: lab.title, url: lab.url }),
    onSuccess: () => {
      setEditing(null);
      refresh();
    },
  });
  const remove = useMutation({ mutationFn: (id: number) => api.deleteLibraryLab(id), onSuccess: refresh });

  const topics = library.data?.topics ?? [];
  const all: LibraryLab[] = topics.flatMap((t) => t.labs.map((l) => ({ ...l, topic: t.name })));
  const filtered = all.filter((l) => (!topic || l.topic === topic) && (!query || `${l.title} ${l.topic} ${l.url}`.toLowerCase().includes(query)));

  return (
    <div className="space-y-4">
      <Card title="Add a lab">
        <form
          className="grid gap-2 lg:grid-cols-[1fr_2fr_2fr_auto]"
          onSubmit={(e) => {
            e.preventDefault();
            add.mutate();
          }}
        >
          <Input required maxLength={120} list="library-topics" value={draft.topic} onChange={(e) => setDraft({ ...draft, topic: e.target.value })} placeholder="Topic" aria-label="Topic" />
          <Input required maxLength={300} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} placeholder="Lab title" aria-label="Lab title" />
          <Input required type="url" maxLength={500} value={draft.url} onChange={(e) => setDraft({ ...draft, url: e.target.value })} placeholder="https://…" aria-label="Lab link" />
          <Button type="submit" busy={add.isPending}>
            Add lab
          </Button>
          <datalist id="library-topics">
            {topics.map((t) => (
              <option key={t.name} value={t.name} />
            ))}
          </datalist>
        </form>
        <p className="mt-2 text-xs text-muted">Pick an existing topic or type a new one. New topics appear at the end of the student library.</p>
        <div className="mt-2">
          <ErrorText error={add.error} />
        </div>
      </Card>

      <Card title={`Library (${library.data?.total ?? 0} labs)`}>
        <div className="mb-3 grid gap-3 sm:grid-cols-2">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search title, topic or link" aria-label="Search the library" />
          <Select value={topic} onChange={(e) => setTopic(e.target.value)} aria-label="Topic filter">
            <option value="">All topics</option>
            {topics.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name} ({t.labs.length})
              </option>
            ))}
          </Select>
        </div>
        <ErrorText error={library.error ?? save.error ?? remove.error} />
        {library.isPending ? (
          <Spinner />
        ) : filtered.length === 0 ? (
          <EmptyState>No labs match.</EmptyState>
        ) : (
          <ul className="divide-y divide-line rounded-lg border border-line">
            {filtered.slice(0, SHOW).map((l) =>
              editing?.id === l.id ? (
                <li key={l.id} className="p-3">
                  <form
                    className="grid gap-2 lg:grid-cols-[1fr_2fr_2fr_auto_auto]"
                    onSubmit={(e) => {
                      e.preventDefault();
                      save.mutate(editing);
                    }}
                  >
                    <Input required list="library-topics" value={editing.topic} onChange={(e) => setEditing({ ...editing, topic: e.target.value })} aria-label="Topic" />
                    <Input required value={editing.title} onChange={(e) => setEditing({ ...editing, title: e.target.value })} aria-label="Lab title" />
                    <Input required type="url" value={editing.url} onChange={(e) => setEditing({ ...editing, url: e.target.value })} aria-label="Lab link" />
                    <Button type="submit" className="px-3 py-1" busy={save.isPending}>
                      Save
                    </Button>
                    <Button type="button" variant="ghost" className="px-3 py-1" onClick={() => setEditing(null)}>
                      Cancel
                    </Button>
                  </form>
                </li>
              ) : (
                <li key={l.id} className="flex flex-wrap items-center gap-3 px-3 py-2 text-sm">
                  <span className="w-44 shrink-0 truncate text-xs text-muted" title={l.topic}>
                    {l.topic}
                  </span>
                  <a href={l.url} target="_blank" rel="noopener noreferrer" className="min-w-0 flex-1 hover:text-accent hover:underline">
                    {l.title}
                  </a>
                  <Button variant="ghost" className="px-2 py-1" onClick={() => setEditing(l)}>
                    Edit
                  </Button>
                  <Button
                    variant="dangerGhost"
                    className="px-2 py-1"
                    busy={remove.isPending && remove.variables === l.id}
                    onClick={() => {
                      if (window.confirm(`Remove "${l.title}" from the library? Exams that already use it keep their copy.`)) remove.mutate(l.id);
                    }}
                  >
                    Delete
                  </Button>
                </li>
              ),
            )}
          </ul>
        )}
        {filtered.length > SHOW && (
          <p className="mt-3 text-xs text-muted">
            Showing {SHOW} of {filtered.length}. Search or pick a topic to find a specific lab.
          </p>
        )}
      </Card>
    </div>
  );
}
