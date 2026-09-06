import { describe, expect, it } from "vitest";
import type { DiffFile } from "./lib/gitDiff";
import { run } from "./validate-doc-freshness";

describe("validate-doc-freshness run()", () => {
  const closeoutFiles: DiffFile[] = [
    {
      path: "sprints/sprint-13-example-feature/README.md",
      addedLines: ["Sprint Status: ✅ Complete and deployed (commit `df2e394`)"],
    },
  ];

  it("exits 1 when a sprint closes out without .ai/CONTEXT.md in the same commit", () => {
    const result = run(
      closeoutFiles,
      ["sprints/sprint-13-example-feature/README.md"],
      "feat: add example feature (Sprint 13)",
    );
    expect(result).toBe(1);
  });

  it("exits 0 when .ai/CONTEXT.md is part of the same commit", () => {
    const result = run(
      closeoutFiles,
      ["sprints/sprint-13-example-feature/README.md", ".ai/CONTEXT.md"],
      "feat: add example feature (Sprint 13)",
    );
    expect(result).toBe(0);
  });

  it("exits 0 when a Docs-Deferred trailer is present", () => {
    const message =
      "feat: add example feature (Sprint 13)\n\nDocs-Deferred: CONTEXT.md refresh follows separately";
    const result = run(
      closeoutFiles,
      ["sprints/sprint-13-example-feature/README.md"],
      message,
    );
    expect(result).toBe(0);
  });

  it("exits 0 for a commit that never closes out a sprint", () => {
    const files: DiffFile[] = [
      {
        path: "sprints/sprint-15-directory-data-entries/README.md",
        addedLines: ["| F-011 | Add new listing | Medium | Completed |"],
      },
    ];
    expect(
      run(files, ["sprints/sprint-15-directory-data-entries/README.md"], "feat: Sprint 15, F-011"),
    ).toBe(0);
  });
});
