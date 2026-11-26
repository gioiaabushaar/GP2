"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ButtonLink, EmptyState, PageHeader, Spinner } from "@/components/ui";

/** "Active Lab" in the sidebar: open the running lab, else the last challenge opened (from the activity log). */
export default function ActiveLabIndex() {
  const router = useRouter();
  const labs = useQuery({ queryKey: ["my-labs"], queryFn: api.myLabs });
  const lastOpened = useQuery({ queryKey: ["last-opened"], queryFn: api.lastOpened });
  const target = labs.data?.find((l) => l.status === "running")?.challenge_id ?? lastOpened.data?.challenge_id;
  const loading = labs.isPending || lastOpened.isPending;

  useEffect(() => {
    if (!loading && target) router.replace(`/lab/${target}`);
  }, [loading, target, router]);

  if (loading || target) return <Spinner />;
  return (
    <>
      <PageHeader title="Active Lab" />
      <EmptyState>You have no active lab yet.</EmptyState>
      <div className="mt-4">
        <ButtonLink href="/challenges">Browse Challenges</ButtonLink>
      </div>
    </>
  );
}
