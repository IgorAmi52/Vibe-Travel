import { toPackageCardViewModels } from "../mapPackageView";
import type { SessionSnapshot } from "../types";
import {
  fixtureExploratory,
  fixturePrimary,
  fixtureRefined,
  type MockFixtureSet,
} from "./fixtures";

function delay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

function randomDelay() {
  return delay(800 + Math.floor(Math.random() * 700));
}

function snapshotFromFixture(sessionId: string, set: MockFixtureSet): SessionSnapshot {
  const tagsPerCard = set.extras.map((e) => e.cardTags);
  const packages = toPackageCardViewModels(set.rows, {
    explicitTagsPerCard: tagsPerCard,
  });
  return {
    sessionId,
    displayTheme: set.displayTheme,
    tripFactsLine: set.tripFactsLine,
    intentChips: [...set.intentChips],
    packages,
  };
}

type SessionMode = "primary" | "refined" | "exploratory";

interface StoredSession {
  mode: SessionMode;
  removedChips: Set<string>;
}

const sessions = new Map<string, StoredSession>();

let seq = 0;
function nextId() {
  seq += 1;
  return `sess-mock-${seq}`;
}

function pickFixture(mode: SessionMode): MockFixtureSet {
  switch (mode) {
    case "refined":
      return fixtureRefined;
    case "exploratory":
      return fixtureExploratory;
    default:
      return fixturePrimary;
  }
}

export async function mockStartSession(query: string): Promise<SessionSnapshot> {
  void query;
  await randomDelay();
  const sessionId = nextId();
  sessions.set(sessionId, { mode: "primary", removedChips: new Set() });
  return snapshotFromFixture(sessionId, fixturePrimary);
}

export async function mockRefineSession(
  sessionId: string,
  message: string,
): Promise<SessionSnapshot> {
  void message;
  await randomDelay();
  const s = sessions.get(sessionId);
  if (!s) {
    const sid = nextId();
    sessions.set(sid, { mode: "refined", removedChips: new Set() });
    return snapshotFromFixture(sid, fixtureRefined);
  }
  s.mode = "refined";
  return snapshotFromFixture(sessionId, pickFixture("refined"));
}

export async function mockRemoveIntentChip(
  sessionId: string,
  chip: string,
): Promise<SessionSnapshot> {
  await randomDelay();
  const s = sessions.get(sessionId);
  if (!s) {
    return mockStartSession("");
  }
  s.removedChips.add(chip);
  const base =
    s.mode === "refined" ? fixtureRefined : fixturePrimary;
  let nextSet: MockFixtureSet = {
    ...base,
    intentChips: base.intentChips.filter((c) => !s.removedChips.has(c)),
  };
  if (nextSet.intentChips.length === 0) {
    nextSet = { ...fixtureExploratory, intentChips: [] };
    s.mode = "exploratory";
  }
  if (s.removedChips.size >= 2) {
    s.mode = "exploratory";
    nextSet = {
      ...fixtureExploratory,
      intentChips: nextSet.intentChips,
    };
  }
  return snapshotFromFixture(sessionId, nextSet);
}
