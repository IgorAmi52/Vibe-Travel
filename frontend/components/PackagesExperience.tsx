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
    setPackages: (p: PackageCardViewModel[]) => void;
    setTripFactsLine: (s: string) => void;
    setIntentChips: (c: string[]) => void;
    setClarificationPrompt: (s: string | null) => void;
  },
) {
  setters.setSessionId(snap.sessionId);
  setters.setDisplayTheme(snap.displayTheme);
  setters.setPackages(snap.packages);
  setters.setTripFactsLine(snap.tripFactsLine);
  setters.setIntentChips(snap.intentChips);
  setters.setClarificationPrompt(snap.clarificationPrompt ?? null);
}

export function PackagesExperience() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [displayTheme, setDisplayTheme] = useState(
    "Discover flight + hotel packages matched to your vibe",
  );
  const [packages, setPackages] = useState<PackageCardViewModel[]>([]);
  const [tripFactsLine, setTripFactsLine] = useState("");
  const [intentChips, setIntentChips] = useState<string[]>([]);
  const [clarificationPrompt, setClarificationPrompt] = useState<
    string | null
  >(null);
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
    setPackages,
    setTripFactsLine,
    setIntentChips,
    setClarificationPrompt,
  };

  async function handleSubmit() {
    const q = refineInput.trim();
    if (!q || loading) return;
    setLoading(true);
    setStatusIdx(0);
    setClarificationPrompt(null);
    try {
      let snap: SessionSnapshot;
      if (!sessionId) {
        snap = await startSession(q);
      } else {
        snap = await refineSession(sessionId, q);
      }
      applySnapshot(snap, setters);
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
    <div className="min-h-screen bg-ss-page font-sans text-slate-900">
      <AppChrome />
      <SearchSummaryBar
        displayTheme={displayTheme}
        tripFactsLine={tripFactsLine}
        intentChips={intentChips}
        onRemoveChip={handleRemoveChip}
        clarificationPrompt={clarificationPrompt}
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
