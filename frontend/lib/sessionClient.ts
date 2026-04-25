import { toPackageCardViewModels } from "./mapPackageView";
import {
  mockRefineSession,
  mockRemoveIntentChip,
  mockStartSession,
} from "./mock/sessionMock";
import type { PackageResultV0, SessionSnapshot } from "./types";

function getApiBase(): string | undefined {
  if (typeof process === "undefined") return undefined;
  const b = process.env.NEXT_PUBLIC_API_BASE_URL;
  return b && b.length > 0 ? b.replace(/\/$/, "") : undefined;
}

function heuristicTheme(query: string): string {
  const q = query.trim();
  if (!q) return "Your next trip, matched to how you like to travel";
  return `Ideas based on: “${q.slice(0, 80)}${q.length > 80 ? "…" : ""}”`;
}

function heuristicTripLine(): string {
  return "Select dates and party size when you continue to Skyscanner";
}

/** Map FastAPI-style JSON to SessionSnapshot (snake_case tolerant). */
function normalizeApiSnapshot(data: Record<string, unknown>): SessionSnapshot {
  const sessionId = String(data.session_id ?? data.sessionId ?? "");
  const results = (data.results ?? []) as PackageResultV0[];
  const packages = toPackageCardViewModels(results);
  const displayTheme = String(
    data.display_theme ?? data.displayTheme ?? heuristicTheme(""),
  );
  const tripFactsLine = String(
    data.trip_facts_line ?? data.tripFactsLine ?? heuristicTripLine(),
  );
  const rawChips = data.intent_chips ?? data.intentChips;
  const intentChips = Array.isArray(rawChips)
    ? rawChips.map(String)
    : [];
  return {
    sessionId,
    displayTheme,
    tripFactsLine,
    intentChips,
    packages,
  };
}

async function apiStartSession(query: string): Promise<SessionSnapshot> {
  const base = getApiBase();
  if (!base) throw new Error("API base not configured");
  const res = await fetch(`${base}/session/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    throw new Error(`session/start failed: ${res.status}`);
  }
  const data = (await res.json()) as Record<string, unknown>;
  const snap = normalizeApiSnapshot(data);
  if (!snap.displayTheme) {
    snap.displayTheme = heuristicTheme(query);
  }
  return snap;
}

async function apiRefineSession(
  sessionId: string,
  message: string,
): Promise<SessionSnapshot> {
  const base = getApiBase();
  if (!base) throw new Error("API base not configured");
  const res = await fetch(`${base}/session/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) {
    throw new Error(`session/refine failed: ${res.status}`);
  }
  const data = (await res.json()) as Record<string, unknown>;
  return normalizeApiSnapshot(data);
}

export async function startSession(query: string): Promise<SessionSnapshot> {
  const base = getApiBase();
  if (!base) {
    return mockStartSession(query);
  }
  try {
    return await apiStartSession(query);
  } catch {
    return mockStartSession(query);
  }
}

export async function refineSession(
  sessionId: string,
  message: string,
): Promise<SessionSnapshot> {
  const base = getApiBase();
  if (!base) {
    return mockRefineSession(sessionId, message);
  }
  try {
    return await apiRefineSession(sessionId, message);
  } catch {
    return mockRefineSession(sessionId, message);
  }
}

export async function removeIntentChip(
  sessionId: string,
  chip: string,
): Promise<SessionSnapshot> {
  const base = getApiBase();
  if (!base) {
    return mockRemoveIntentChip(sessionId, chip);
  }
  try {
    const res = await fetch(`${base}/session/refine`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message: `remove intent tag: ${chip}`,
      }),
    });
    if (!res.ok) throw new Error(String(res.status));
    const data = (await res.json()) as Record<string, unknown>;
    return normalizeApiSnapshot(data);
  } catch {
    return mockRemoveIntentChip(sessionId, chip);
  }
}
