#!/usr/bin/env tsx
import { join } from "node:path";
import { findSprintConsistencyIssues } from "./lib/docChecks";
import { isMainModule } from "./lib/isMainModule";

/**
 * Usage: npm run validate:sprint-consistency
 *
 * For every sprints/sprint- (wildcard) folder, if every row in README.md's
 * Features table is the exact plain word "Completed", tasks.md for that same
 * sprint must have zero remaining `- [ ]` lines — guards against a
 * README.md that's accurate while tasks.md still has stale unchecked boxes
 * nobody went back to flip. Doesn't need a diff — runs against the current
 * repo state.
 */
export function run(findings: ReturnType<typeof findSprintConsistencyIssues>): number {
  if (findings.length === 0) {
    console.log("Every sprint's README.md Features table agrees with its tasks.md checkboxes.");
    return 0;
  }

  console.error(`Found ${findings.length} sprint(s) with an inconsistency:\n`);
  for (const finding of findings) {
    console.error(
      `  ${finding.sprintDir}: README.md's Features table is 100% "Completed", but tasks.md has ` +
        `${finding.unchecked.length} unchecked box(es):`,
    );
    for (const line of finding.unchecked) {
      console.error(`    ${line}`);
    }
  }
  console.error(
    "\nEither the tasks.md checkboxes are stale (flip them to match README.md), or README.md " +
      'overclaims (correct a Feature\'s status back from plain "Completed").',
  );
  return 1;
}

function main() {
  const sprintsDir = join(process.cwd(), "sprints");
  process.exitCode = run(findSprintConsistencyIssues(sprintsDir));
}

if (isMainModule(import.meta.url)) {
  main();
}
