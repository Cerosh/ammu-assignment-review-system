#!/usr/bin/env tsx
import { findMissingSprintDocContact, getDocsDeferredReason } from "./lib/docChecks";
import {
  getRangeCommitMessages,
  getRangeFilePaths,
  getStagedFilePaths,
  readCommitMessageFile,
} from "./lib/gitDiff";
import { isMainModule } from "./lib/isMainModule";

/**
 * Usage:
 *   npm run validate:sprint-doc-contact -- <commit-msg-file>   (commit-msg hook — local)
 *   npm run validate:sprint-doc-contact -- --range <base> <head>   (CI)
 *
 * If a commit references a sprint (e.g. "Sprint 11", "Sprint 09b") and touches
 * application code, at least one file under that sprint's own
 * sprints/sprint-{NN}- (wildcard) folder must be part of the same commit —
 * guards against implementation commits that never touch the sprint's own
 * docs. Only meaningful once commit messages consistently include a
 * "(Sprint NN)" reference (see scripts/lib/docChecks.ts). Bypass with a
 * `Docs-Deferred: <reason>` trailer in the commit message — visible in
 * `git log`, not a silent skip.
 */
export function run(commitMessage: string, touchedPaths: string[]): number {
  const deferredReason = getDocsDeferredReason(commitMessage);
  const finding = findMissingSprintDocContact(commitMessage, touchedPaths);

  if (!finding) {
    return 0;
  }

  if (deferredReason) {
    console.log(
      `Sprint ${finding.sprintNumber}'s docs weren't touched, but explicitly deferred: "${deferredReason}"`,
    );
    return 0;
  }

  console.error(
    `This commit references Sprint ${finding.sprintNumber} and touches application code, ` +
      `but doesn't touch any file under ${finding.expectedGlob}.`,
  );
  console.error(
    "\nUpdate that sprint's README.md/tasks.md in this same commit, or add a " +
      "`Docs-Deferred: <reason>` trailer to the commit message if this genuinely should wait.",
  );
  return 1;
}

function main() {
  const args = process.argv.slice(2);
  const rangeIndex = args.indexOf("--range");

  if (rangeIndex === -1 && !args[0]) {
    // This check inherently needs a real commit message to parse a
    // "Sprint NN" reference out of — nothing meaningful to do without one
    // (e.g. an ad hoc `npm run validate:docs` against staged changes with
    // no commit in progress yet).
    console.log(
      "validate:sprint-doc-contact needs a commit message — skipping (no commit in progress).",
    );
    return;
  }

  const commitMessage =
    rangeIndex === -1
      ? readCommitMessageFile(args[0])
      : getRangeCommitMessages(args[rangeIndex + 1], args[rangeIndex + 2]);
  const touchedPaths =
    rangeIndex === -1
      ? getStagedFilePaths()
      : getRangeFilePaths(args[rangeIndex + 1], args[rangeIndex + 2]);

  process.exitCode = run(commitMessage, touchedPaths);
}

if (isMainModule(import.meta.url)) {
  main();
}
