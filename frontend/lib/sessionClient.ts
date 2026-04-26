import { mapInvokeToSnapshot } from "./mapInvokeResponse";
import {
  mockRefineSession,
  mockStartSession,
} from "./mock/sessionMock";
import type { InvokeResponse, InvokeState, SessionSnapshot } from "./types";

const INVOKE_URL = "/api/invoke";

let lastState: InvokeState | null = null;

export function getLastState(): InvokeState | null {
  return lastState;
}

async function postInvoke(
  body: Record<string, unknown>,
): Promise<InvokeResponse> {
  const res = await fetch(INVOKE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = (await res.json()) as InvokeResponse & { error?: string };
  if (!res.ok) {
    throw new Error(data.error ?? `invoke failed: ${res.status}`);
  }
  return data;
}

export async function startSession(query: string): Promise<SessionSnapshot> {
  try {
    const response = await postInvoke({
      type: "NEW",
      user_query: query,
      source: "web",
      mode: "gemini",
    });
    lastState = response.state;
    return mapInvokeToSnapshot(response);
  } catch (err) {
    console.error("[invoke] startSession failed, falling back to mock", err);
    return mockStartSession(query);
  }
}

export async function refineSession(
  _sessionId: string,
  message: string,
): Promise<SessionSnapshot> {
  if (!lastState) {
    return startSession(message);
  }
  try {
    const response = await postInvoke({
      type: "CLARIFICATION",
      user_query: message,
      source: "web",
      mode: "gemini",
      state: lastState,
    });
    lastState = response.state;
    return mapInvokeToSnapshot(response);
  } catch (err) {
    console.error("[invoke] refineSession failed, falling back to mock", err);
    return mockRefineSession(_sessionId, message);
  }
}

export async function removeIntentChip(
  sessionId: string,
  chip: string,
): Promise<SessionSnapshot> {
  return refineSession(sessionId, `remove: ${chip}`);
}
