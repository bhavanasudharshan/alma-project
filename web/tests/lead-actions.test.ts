/**
 * Regression test for the NEXT_ACTION table (`lib/lead-actions.ts`).
 *
 * NOTES.md mistake #15: the table originally lived inside a `"use client"` module, so
 * a server component importing it received a client-reference proxy and every lookup
 * silently produced `undefined` — the action buttons vanished with no error. These
 * tests pin the shape for every LeadState so that failure mode cannot come back (E1).
 */

import { describe, expect, it } from "vitest";

import { LEAD_STATES, type LeadState } from "@/lib/api";
import { NEXT_ACTION, type NextAction } from "@/lib/lead-actions";

/** How `page.tsx` reads the table: a real action, or a terminal state. */
function nextActionFor(state: LeadState): NextAction | null {
  return NEXT_ACTION[state] ?? null;
}

describe("NEXT_ACTION covers every LeadState", () => {
  it("knows about exactly the three pipeline states", () => {
    expect([...LEAD_STATES]).toEqual(["PENDING", "REACHED_OUT", "QUALIFIED"]);
  });

  for (const state of LEAD_STATES) {
    it(`resolves ${state} to an action or an explicit null, never a broken lookup`, () => {
      const action = nextActionFor(state);
      expect(action).not.toBeUndefined();

      if (action === null) return;
      // A real object, not a client-reference proxy: every field must be a string.
      expect(typeof action.target).toBe("string");
      expect(typeof action.label).toBe("string");
      expect(typeof action.pendingLabel).toBe("string");
      expect(action.label.length).toBeGreaterThan(0);
      expect(action.pendingLabel.length).toBeGreaterThan(0);
      expect(LEAD_STATES).toContain(action.target);
      expect(action.target).not.toBe(state);
    });
  }
});

describe("NEXT_ACTION mirrors the API's transition table", () => {
  it("advances PENDING to REACHED_OUT", () => {
    expect(nextActionFor("PENDING")).toEqual({
      target: "REACHED_OUT",
      label: "Mark reached out",
      pendingLabel: "Saving…",
    });
  });

  it("advances REACHED_OUT to QUALIFIED", () => {
    expect(nextActionFor("REACHED_OUT")).toEqual({
      target: "QUALIFIED",
      label: "Mark qualified",
      pendingLabel: "Saving…",
    });
  });

  it("treats QUALIFIED as terminal", () => {
    expect(nextActionFor("QUALIFIED")).toBeNull();
  });

  it("terminates: following the chain from PENDING reaches a terminal state", () => {
    const seen: LeadState[] = [];
    let state: LeadState | null = "PENDING";
    while (state) {
      expect(seen).not.toContain(state);
      seen.push(state);
      state = nextActionFor(state)?.target ?? null;
    }
    expect(seen).toEqual(["PENDING", "REACHED_OUT", "QUALIFIED"]);
  });

  it("offers no action outside the known states", () => {
    for (const key of Object.keys(NEXT_ACTION)) {
      expect(LEAD_STATES).toContain(key as LeadState);
    }
  });
});
