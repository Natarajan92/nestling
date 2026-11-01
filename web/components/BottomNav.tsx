"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAskSheet } from "./AskSheet";

const ITEMS = [
  { href: "/", label: "Today", icon: "🌤️" },
  { href: "/journeys", label: "Journeys", icon: "🧭" },
  { href: "/lessons", label: "Lessons", icon: "🎬" },
  { href: "/memory", label: "Memory", icon: "📔" },
];

export default function BottomNav() {
  const path = usePathname();
  const { open, setOpen } = useAskSheet();
  if (path.startsWith("/welcome")) return null;
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-10 border-t border-ink/5 bg-cream/95 backdrop-blur"
    >
      <ul className="mx-auto flex max-w-md justify-between px-3 pb-[env(safe-area-inset-bottom)]">
        {ITEMS.map(({ href, label, icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <li key={href} className="flex-1">
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex flex-col items-center gap-0.5 py-2.5 text-xs ${active ? "font-semibold text-ink" : "text-ink-soft"}`}
              >
                <span
                  aria-hidden
                  className={`rounded-full px-3 py-0.5 text-lg transition-colors ${active ? "bg-peach/40" : ""}`}
                >
                  {icon}
                </span>
                {label}
              </Link>
            </li>
          );
        })}
        <li className="flex-1">
          <button
            type="button"
            aria-haspopup="dialog"
            aria-expanded={open}
            onClick={() => setOpen(true)}
            className="flex w-full flex-col items-center gap-0.5 py-2.5 text-xs text-ink-soft"
          >
            <span aria-hidden className={`rounded-full px-3 py-0.5 text-lg ${open ? "bg-peach/40" : ""}`}>
              💬
            </span>
            Ask
          </button>
        </li>
      </ul>
    </nav>
  );
}
