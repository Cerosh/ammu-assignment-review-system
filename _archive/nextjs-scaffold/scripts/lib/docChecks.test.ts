import { describe, expect, it } from "vitest";
import type { DiffFile } from "./gitDiff";
import {
  checkSprintConsistency,
  findMissingContextUpdate,
  findMissingSprintDocContact,
  findSelfContradictions,
  getDocsDeferredReason,
} from "./docChecks";

function diffFile(path: string, addedLines: string[]): DiffFile {
  return { path, addedLines };
}

describe("findSelfContradictions (Check 1)", () => {
  it("flags 'not yet committed/deployed' text added in the commit being made", () => {
    const files = [
      diffFile("sprints/sprint-13-example-feature/README.md", [
        "Sprint Status: ✅ Complete locally (not yet committed/deployed)",
      ]),
    ];
    const findings = findSelfContradictions(files);
    expect(findings).toHaveLength(1);
    expect(findings[0].file).toBe("sprints/sprint-13-example-feature/README.md");
  });

  it("flags the 'commit/push/deploy remain open' phrasing", () => {
    const files = [
      diffFile("sprints/sprint-11-home-tutoring-listing/retrospective.md", [
        "Commit / push / deploy this sprint's changes remain open steps for the project owner.",
      ]),
    ];
    expect(findSelfContradictions(files)).toHaveLength(1);
  });

  it("does not flag genuinely-future statements unrelated to this commit", () => {
    const files = [
      diffFile(".ai/ARCHITECTURE.md", ["Supabase", "(Future)"]),
      diffFile("sprints/sprint-10-future-platform/README.md", [
        "Sprint Status: 🟡 Future — not started, awaiting explicit instruction.",
      ]),
    ];
    expect(findSelfContradictions(files)).toEqual([]);
  });

  it("does not flag removed lines (only scans added lines by design)", () => {
    // parseUnifiedDiff never includes removed lines in addedLines, so a
    // DiffFile fixture representing "this phrase was deleted" simply has
    // no addedLines for it — nothing to assert beyond the empty case.
    const files = [diffFile("sprints/sprint-13-example-feature/README.md", [])];
    expect(findSelfContradictions(files)).toEqual([]);
  });

  it("does not flag the guardrail scripts themselves or their tests", () => {
    const files = [
      diffFile("scripts/lib/docChecks.ts", ["/not yet committed/i,"]),
      diffFile("scripts/validate-no-self-contradiction.test.ts", [
        '{ addedLines: ["not yet deployed"] },',
      ]),
    ];
    expect(findSelfContradictions(files)).toEqual([]);
  });
});

describe("findMissingSprintDocContact (Check 2)", () => {
  it("flags a sprint-referencing commit that touches code but not that sprint's docs", () => {
    const finding = findMissingSprintDocContact("feat: implement homepage experience (Sprint 02)", [
      "app/(home)/page.tsx",
      "features/homepage/Hero.tsx",
    ]);
    expect(finding).not.toBeNull();
    expect(finding?.sprintNumber).toBe("02");
  });

  it("does not flag when the matching sprint's docs are also touched", () => {
    const finding = findMissingSprintDocContact(
      "feat: implement Sprint 11 (Home Tutoring Listing)",
      [
        "app/api/carpark/route.ts",
        "features/homepage/TransitWidget.tsx",
        "sprints/sprint-11-home-tutoring-listing/README.md",
      ],
    );
    expect(finding).toBeNull();
  });

  it("handles a lettered sprint suffix (e.g. Sprint 09b)", () => {
    const finding = findMissingSprintDocContact("feat: implement Sprint 09b (Content Cleanup)", [
      "lib/services/searchService.ts",
    ]);
    expect(finding?.sprintNumber).toBe("09b");
    expect(finding?.expectedGlob).toContain("sprint-09b-");
  });

  it("does not flag a commit with no sprint reference at all", () => {
    expect(findMissingSprintDocContact("fix: correct a typo", ["app/layout.tsx"])).toBeNull();
  });

  it("does not flag a sprint-referencing commit that touches no application code", () => {
    expect(
      findMissingSprintDocContact("docs: plan Sprint 09b (Content Cleanup)", [
        "sprints/sprint-09b-content-cleanup/README.md",
      ]),
    ).toBeNull();
  });
});

describe("checkSprintConsistency (Check 3)", () => {
  const allCompletedReadme = `
| ID | Feature | Priority | Status |
|----|----------|----------|--------|
| F-001 | Security headers | High | Completed |
| F-002 | Robots.txt | High | Completed |
`;

  it("flags unchecked tasks.md boxes when every Feature row is plain 'Completed'", () => {
    const tasks = "- [x] Done thing\n- [ ] Forgotten thing\n- [ ] Another forgotten thing\n";
    const unchecked = checkSprintConsistency(allCompletedReadme, tasks);
    expect(unchecked).toHaveLength(2);
  });

  it("does not flag when tasks.md is fully checked", () => {
    const tasks = "- [x] Done thing\n- [x] Also done\n";
    expect(checkSprintConsistency(allCompletedReadme, tasks)).toEqual([]);
  });

  it("does not flag when not every Feature is plain 'Completed' (e.g. one Deferred)", () => {
    const partialReadme = `
| ID | Feature | Priority | Status |
|----|----------|----------|--------|
| F-001 | Analytics | High | Completed |
| F-002 | Sentry | High | Deferred — project owner chose not to set up an account |
`;
    const tasks = "- [ ] Install Sentry\n";
    expect(checkSprintConsistency(partialReadme, tasks)).toEqual([]);
  });

  it("does not flag a compound 'Completed (...)' status as plain Completed", () => {
    const compoundReadme = `
| ID | Feature | Priority | Status |
|----|----------|----------|--------|
| F-001 | Browser compatibility | Medium | Completed (automated proxy; physical-device testing disclosed as unavailable) |
`;
    const tasks = "- [ ] Manually verify on a real iOS device\n";
    expect(checkSprintConsistency(compoundReadme, tasks)).toEqual([]);
  });

  it("returns no findings when there is no tasks.md for the sprint", () => {
    expect(checkSprintConsistency(allCompletedReadme, null)).toEqual([]);
  });
});

describe("findMissingContextUpdate (Check 4)", () => {
  it("flags a sprint closing out without CONTEXT.md in the same commit", () => {
    const files = [
      diffFile("sprints/sprint-13-example-feature/README.md", [
        "Sprint Status: ✅ Complete and deployed (commit `df2e394`)",
      ]),
    ];
    const finding = findMissingContextUpdate(files, [
      "sprints/sprint-13-example-feature/README.md",
    ]);
    expect(finding).not.toBeNull();
  });

  it("does not flag when CONTEXT.md is part of the same commit", () => {
    const files = [
      diffFile("sprints/sprint-13-example-feature/README.md", [
        "Sprint Status: ✅ Complete and deployed (commit `df2e394`)",
      ]),
    ];
    const finding = findMissingContextUpdate(files, [
      "sprints/sprint-13-example-feature/README.md",
      ".ai/CONTEXT.md",
    ]);
    expect(finding).toBeNull();
  });

  it("does not flag routine commits that never touch a Sprint Status line", () => {
    const files = [
      diffFile("sprints/sprint-15-directory-data-entries/README.md", [
        "| F-011 | Add new dance studio listing | Medium | Completed |",
      ]),
    ];
    const finding = findMissingContextUpdate(files, [
      "sprints/sprint-15-directory-data-entries/README.md",
    ]);
    expect(finding).toBeNull();
  });

  it("does not flag a Sprint Status line outside a sprint README (e.g. a quote in notes.md)", () => {
    const files = [
      diffFile("sprints/sprint-13-example-feature/notes.md", [
        "As a reminder, README.md says 'Sprint Status: ✅ Complete and deployed'.",
      ]),
    ];
    expect(
      findMissingContextUpdate(files, ["sprints/sprint-13-example-feature/notes.md"]),
    ).toBeNull();
  });
});

describe("getDocsDeferredReason (escape hatch)", () => {
  it("extracts the reason from a Docs-Deferred trailer", () => {
    const message =
      "fix: emergency hotfix for production 500\n\nDocs-Deferred: no time, will follow up";
    expect(getDocsDeferredReason(message)).toBe("no time, will follow up");
  });

  it("returns null when no trailer is present", () => {
    expect(getDocsDeferredReason("feat: implement Sprint 11 (Home Tutoring Listing)")).toBeNull();
  });
});
