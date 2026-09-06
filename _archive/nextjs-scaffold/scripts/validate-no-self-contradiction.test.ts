import { describe, expect, it } from "vitest";
import type { DiffFile } from "./lib/gitDiff";
import { run } from "./validate-no-self-contradiction";

describe("validate-no-self-contradiction run()", () => {
  it("exits 1 when a self-contradiction is found", () => {
    const files: DiffFile[] = [
      {
        path: "sprints/sprint-13-example-feature/README.md",
        addedLines: ["not yet deployed"],
      },
    ];
    expect(run(files, "feat: add example feature (Sprint 13)")).toBe(1);
  });

  it("exits 0 when nothing is found", () => {
    const files: DiffFile[] = [{ path: "README.md", addedLines: ["Everything is fine here."] }];
    expect(run(files, "chore: tidy up README")).toBe(0);
  });

  it("exits 0 for an empty diff", () => {
    expect(run([], "chore: no-op")).toBe(0);
  });

  it("exits 0 when a Docs-Deferred trailer is present", () => {
    const files: DiffFile[] = [
      {
        path: "sprints/sprint-16-backlog/README.md",
        addedLines: ["quoting the old 'not yet deployed' text"],
      },
    ];
    const message =
      "docs: record the doc audit findings\n\nDocs-Deferred: historical quote, not a live claim";
    expect(run(files, message)).toBe(0);
  });
});
