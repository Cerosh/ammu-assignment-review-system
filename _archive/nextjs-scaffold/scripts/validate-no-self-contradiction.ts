#!/usr/bin/env tsx
import { findSelfContradictions, getDocsDeferredReason } from "./lib/docChecks";
import {
  getRangeCommitMessages,
  getRangeDiff,
  getStagedDiff,
  readCommitMessageFile,
} from "./lib/gitDiff";
import { isMainModule } from "./lib/isMainModule";

/**
 * Usage:
 *   npm run validate:no-contradiction -- <commit-msg-file>     (commit-msg hook — local)
 *   npm run validate:no-contradiction -- --range <base> <head> (CI)
 *
 * Blocks any commit whose added lines contain "not yet committed/deployed"-style
 * text — false by construction, since it's being committed right now. See
 * scripts/lib/docChecks.ts for the full pattern list.
 *
 * Runs as a commit-msg hook (not pre-commit) so the `Docs-Deferred:` escape
 * hatch works — needed in practice: this check can flag documentation *about*
 * the stale-text pattern itself (e.g. backlog notes quoting the exact text
 * being guarded against) as if it were a live claim. scripts/** is exempted
 * outright (see docChecks.ts); anything else that's a legitimate
 * historical/analytical reference uses the trailer instead of being silently
 * allowed everywhere.
 */
export function run(files: ReturnType<typeof getStagedDiff>, commitMessage: string): number {
  const findings = findSelfContradictions(files);

  if (findings.length === 0) {
    return 0;
  }

  const deferredReason = getDocsDeferredReason(commitMessage);
  if (deferredReason) {
    console.log(
      `Found ${findings.length} self-contradiction(s), but explicitly deferred: "${deferredReason}"`,
    );
    return 0;
  }

  console.error(`Found ${findings.length} self-contradiction(s):\n`);
  for (const finding of findings) {
    console.error(`  ${finding.file}: ${finding.message}`);
    console.error(`    "${finding.line}"`);
  }
  console.error(
    "\nThis text claims something isn't done yet, but it's part of the commit making it true " +
      "right now. Either remove/reword the claim, or add a `Docs-Deferred: <reason>` trailer if " +
      "this is a legitimate historical/analytical reference rather than a live status claim.",
  );
  return 1;
}

function main() {
  const args = process.argv.slice(2);
  const rangeIndex = args.indexOf("--range");

  if (rangeIndex === -1) {
    // The commit-msg-file argument is optional for ad hoc local runs (e.g.
    // `npm run validate:docs`, checking staged changes before a message
    // exists) — without it, the Docs-Deferred escape hatch simply can't
    // apply yet, which is the safe default (fails closed, not open).
    const commitMessage = args[0] ? readCommitMessageFile(args[0]) : "";
    process.exitCode = run(getStagedDiff(), commitMessage);
    return;
  }

  const base = args[rangeIndex + 1];
  const head = args[rangeIndex + 2];
  process.exitCode = run(getRangeDiff(base, head), getRangeCommitMessages(base, head));
}

if (isMainModule(import.meta.url)) {
  main();
}
