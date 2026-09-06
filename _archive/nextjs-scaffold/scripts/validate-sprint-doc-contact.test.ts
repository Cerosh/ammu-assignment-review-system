import { describe, expect, it } from "vitest";
import { run } from "./validate-sprint-doc-contact";

describe("validate-sprint-doc-contact run()", () => {
  it("exits 1 when a sprint commit touches code but not that sprint's docs", () => {
    const result = run("feat: implement homepage experience (Sprint 02)", ["app/(home)/page.tsx"]);
    expect(result).toBe(1);
  });

  it("exits 0 when the sprint's own docs are also touched", () => {
    const result = run("feat: implement Sprint 11 (Home Tutoring Listing)", [
      "app/api/carpark/route.ts",
      "sprints/sprint-11-home-tutoring-listing/README.md",
    ]);
    expect(result).toBe(0);
  });

  it("exits 0 when a Docs-Deferred trailer is present, even without doc contact", () => {
    const message =
      "fix: emergency hotfix for Sprint 15 production 500\n\nDocs-Deferred: will follow up tomorrow";
    expect(run(message, ["app/api/emergency/route.ts"])).toBe(0);
  });

  it("exits 0 for a commit with no sprint reference", () => {
    expect(run("fix: correct a typo", ["app/layout.tsx"])).toBe(0);
  });
});
