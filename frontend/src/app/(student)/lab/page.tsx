"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { lastLab } from "@/lib/insights";
import { ButtonLink, EmptyState, PageHeader, Spinner } from "@/components/ui";

/** "Active Lab" in the sidebar: open the running lab, else the last challenge opened. */
export default function ActiveLabIndex() {
  const router = useRouter();
  const labs = useQuery({ queryKey: ["my-labs"], queryFn: api.myLabs });
  const target = labs.data?.find((l) => l.status === "running")?.challenge_id ?? lastLab.get();

  useEffect(() => {
    if (!labs.isPending && target) router.replace(`/lab/${target}`);
  }, [labs.isPending, target, router]);

  if (labs.isPending || target) return <Spinner />;
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
