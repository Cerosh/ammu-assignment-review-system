import { describe, expect, it } from "vitest";
import type { ConsistencyFinding } from "./lib/docChecks";
import { run } from "./validate-sprint-consistency";

describe("validate-sprint-consistency run()", () => {
  it("exits 1 when a sprint has an inconsistency", () => {
    const findings: ConsistencyFinding[] = [
      { sprintDir: "sprint-09-production", unchecked: ["- [ ] Something forgotten"] },
    ];
    expect(run(findings)).toBe(1);
  });

  it("exits 0 when there are no findings", () => {
    expect(run([])).toBe(0);
  });
});
