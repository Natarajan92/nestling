import type { Metadata, Viewport } from "next";
import { Fraunces, Inter } from "next/font/google";
import BottomNav from "@/components/BottomNav";
import { DISCLAIMER } from "@/lib/api";
import "./globals.css";

const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin"] });
const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Nestling",
  description: "A warm, sourced companion for first-time parents in India.",
};

export const viewport: Viewport = { themeColor: "#FFF8F1" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${fraunces.variable} ${inter.variable} antialiased`}>
      <body className="min-h-dvh">
        <div className="mx-auto flex min-h-dvh max-w-md flex-col px-5 pb-28 pt-8">
          <main className="flex-1">{children}</main>
          <footer className="mt-10 text-center text-xs leading-relaxed text-ink-soft">{DISCLAIMER}</footer>
        </div>
        <BottomNav />
      </body>
    </html>
  );
}
