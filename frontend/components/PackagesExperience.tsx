"use client";

import { useEffect, useState } from "react";
import {
  refineSession,
  removeIntentChip,
  startSession,
} from "@/lib/sessionClient";
import type { PackageCardViewModel, SessionSnapshot } from "@/lib/types";
import { AppChrome } from "./AppChrome";
import { ResultsLayout } from "./ResultsLayout";
import { SearchSummaryBar } from "./SearchSummaryBar";

const STATUS_MESSAGES = [
  "Understanding your trip…",
  "Checking live prices…",
  "Matching stays to your vibe…",
];

function applySnapshot(
  snap: SessionSnapshot,
  setters: {
    setSessionId: (id: string) => void;
    setDisplayTheme: (s: string) => void;
    setTripFactsLine: (s: string) => void;
    setIntentChips: (c: string[]) => void;
    setPackages: (p: PackageCardViewModel[]) => void;
  },
) {
  setters.setSessionId(snap.sessionId);
  setters.setDisplayTheme(snap.displayTheme);
  setters.setTripFactsLine(snap.tripFactsLine);
  setters.setIntentChips(snap.intentChips);
  setters.setPackages(snap.packages);
}

export function PackagesExperience() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [displayTheme, setDisplayTheme] = useState(
    "Discover flight + hotel packages matched to your vibe",
  );
  const [tripFactsLine, setTripFactsLine] = useState(
    "Use natural language — we’ll show indicative flight + stay bundles",
  );
  const [intentChips, setIntentChips] = useState<string[]>([]);
  const [packages, setPackages] = useState<PackageCardViewModel[]>([]);
  const [refineInput, setRefineInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusIdx, setStatusIdx] = useState(0);

  useEffect(() => {
    if (!loading) return;
    const t = window.setInterval(() => {
      setStatusIdx((i) => (i + 1) % STATUS_MESSAGES.length);
    }, 2000);
    return () => window.clearInterval(t);
  }, [loading]);

  const setters = {
    setSessionId,
    setDisplayTheme,
    setTripFactsLine,
    setIntentChips,
    setPackages,
  };

  async function handleSubmit() {
    const q = refineInput.trim();
    if (!q || loading) return;
    setLoading(true);
    setStatusIdx(0);
    try {
      if (!sessionId) {
        const snap = await startSession(q);
        applySnapshot(snap, setters);
      } else {
        const snap = await refineSession(sessionId, q);
        applySnapshot(snap, setters);
      }
      setRefineInput("");
    } finally {
      setLoading(false);
    }
  }

  async function handleRemoveChip(chip: string) {
    if (!sessionId || loading) return;
    setLoading(true);
    setStatusIdx(0);
    try {
      const snap = await removeIntentChip(sessionId, chip);
      applySnapshot(snap, setters);
    } finally {
      setLoading(false);
    }
  }

  const refinePlaceholder = sessionId
    ? "Refine your search…"
    : "Describe your trip…";

  return (
    <div className="min-h-screen bg-neutral-100 font-sans text-neutral-900">
      <AppChrome />
      <SearchSummaryBar
        displayTheme={displayTheme}
        tripFactsLine={tripFactsLine}
        intentChips={intentChips}
        onRemoveChip={handleRemoveChip}
        refinePlaceholder={refinePlaceholder}
        refineValue={refineInput}
        onRefineChange={setRefineInput}
        onSubmit={handleSubmit}
        loading={loading}
      />
      <main>
        <ResultsLayout
          packages={packages}
          loading={loading}
          statusMessage={STATUS_MESSAGES[statusIdx] ?? STATUS_MESSAGES[0]}
        />
      </main>
    </div>
  );
}
