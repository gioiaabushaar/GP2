"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { homeFor, useAuth } from "@/lib/auth";
import { Splash } from "@/components/ui";

export default function Home() {
  const { user } = useAuth();
  const router = useRouter();
  useEffect(() => {
    router.replace(user ? homeFor(user) : "/login");
  }, [user, router]);
  return <Splash />;
}
