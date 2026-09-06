#!/usr/bin/env tsx
import { findMissingContextUpdate, getDocsDeferredReason } from "./lib/docChecks";
import {
  getRangeCommitMessages,
  getRangeDiff,
  getRangeFilePaths,
  getStagedDiff,
  getStagedFilePaths,
  readCommitMessageFile,
} from "./lib/gitDiff";
import { isMainModule } from "./lib/isMainModule";

/**
 * Usage:
 *   npm run validate:doc-freshness -- <commit-msg-file>       (commit-msg hook — local)
 *   npm run validate:doc-freshness -- --range <base> <head>   (CI)
 *
 * If this commit adds a "Sprint Status: ...Complete/Deployed/✅" line to a
 * sprint's own README.md — the exact moment a sprint closes out — .ai/CONTEXT.md
 * must be part of the same commit, so the top-level doc doesn't drift out of
 * sync with what's actually shipped. Bypass with a `Docs-Deferred: <reason>`
 * trailer. Runs as a commit-msg hook (not pre-commit) specifically so the
 * escape hatch works — pre-commit runs before the commit message exists.
 */
export function run(
  files: ReturnType<typeof getStagedDiff>,
  touchedPaths: string[],
  commitMessage: string,
): number {
  const finding = findMissingContextUpdate(files, touchedPaths);
  if (!finding) return 0;

  const deferredReason = getDocsDeferredReason(commitMessage);
  if (deferredReason) {
    console.log(
      `${finding.file} closes out a sprint without .ai/CONTEXT.md, but explicitly deferred: "${deferredReason}"`,
    );
    return 0;
  }

  console.error(
    `${finding.file} adds a "Sprint Status: ...Complete/Deployed" line, but .ai/CONTEXT.md isn't ` +
      "part of this commit.",
  );
  console.error(
    "\nUpdate .ai/CONTEXT.md's Current Sprint/Phase/Completed sections in this same commit, or add a " +
      "`Docs-Deferred: <reason>` trailer to the commit message if this genuinely should wait.",
  );
  return 1;
}

function main() {
  const args = process.argv.slice(2);
  const rangeIndex = args.indexOf("--range");

  if (rangeIndex === -1) {
    // Commit-msg-file argument is optional for ad hoc local runs — see the
    // matching comment in validate-no-self-contradiction.ts.
    const commitMessage = args[0] ? readCommitMessageFile(args[0]) : "";
    const files = getStagedDiff();
    const touchedPaths = getStagedFilePaths();
    process.exitCode = run(files, touchedPaths, commitMessage);
    return;
  }

  const base = args[rangeIndex + 1];
  const head = args[rangeIndex + 2];
  const files = getRangeDiff(base, head);
  const touchedPaths = getRangeFilePaths(base, head);
  const commitMessage = getRangeCommitMessages(base, head);
  process.exitCode = run(files, touchedPaths, commitMessage);
}

if (isMainModule(import.meta.url)) {
  main();
}
