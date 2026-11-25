"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { homeFor, useAuth } from "@/lib/auth";
import type { Role } from "@/lib/types";
import { Logo, Splash } from "./ui";

type NavItem = { href: string; label: string; match?: string };

const NAV: Record<Role, NavItem[]> = {
  student: [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/challenges", label: "Challenges" },
    { href: "/lab", label: "Active Lab", match: "/lab" },
    { href: "/web-labs", label: "Web Labs" },
    { href: "/reports", label: "Reports" },
  ],
  instructor: [
    { href: "/instructor", label: "Dashboard" },
    { href: "/instructor/insights", label: "Student Insights" },
    { href: "/instructor/deploy", label: "Deploy Labs" },
    { href: "/instructor/content", label: "Manage Challenges" },
    { href: "/instructor/web-exams", label: "Web Lab Exams" },
  ],
};

/** Page frame for logged-in users: sidebar, role check and the page itself. */
export function AppShell({ role, children }: { role: Role; children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const allowed = user?.role === role;

  useEffect(() => {
    if (!user) router.replace("/login");
    else if (user.role !== role) router.replace(homeFor(user));
  }, [user, role, router]);

  if (!user || !allowed) return <Splash />;

  const isActive = (item: NavItem) => {
    const base = item.match ?? item.href;
    return item.href === "/instructor" ? pathname === base : pathname === base || pathname.startsWith(`${base}/`);
  };

  return (
    <div className="flex min-h-screen">
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-56 flex-col border-r border-line bg-panel transition-transform md:static md:translate-x-0 ${
          menuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="border-b border-line px-5 py-5">
          <Link href={homeFor(user)} onClick={() => setMenuOpen(false)}>
            <Logo />
          </Link>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV[role].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMenuOpen(false)}
              className={`block rounded-lg px-3 py-2 text-sm transition ${
                isActive(item) ? "bg-white/5 font-semibold text-white" : "text-muted hover:bg-white/5 hover:text-white"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="border-t border-line px-5 py-4 text-sm">
          <p className="truncate text-white" title={user.email}>
            {role === "instructor" ? "Instructor" : "Student"}: {user.full_name}
          </p>
          <button onClick={() => logout()} className="mt-1 text-accent hover:underline">
            Logout
          </button>
        </div>
      </aside>

      {menuOpen && <div className="fixed inset-0 z-30 bg-black/50 md:hidden" onClick={() => setMenuOpen(false)} />}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-line px-4 py-3 md:hidden">
          <button aria-label="Open menu" onClick={() => setMenuOpen(true)} className="rounded-md border border-line px-2 py-1 text-white">
            ☰
          </button>
          <Logo className="text-lg" />
        </header>
        <main className="flex-1 px-4 py-6 md:px-8">{children}</main>
      </div>
    </div>
  );
}
