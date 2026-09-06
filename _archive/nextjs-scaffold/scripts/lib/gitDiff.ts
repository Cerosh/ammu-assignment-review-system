import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

/**
 * Shared git plumbing for the doc-staleness guardrail scripts. Each check
 * script only ever deals with parsed diff/commit data from here, never a raw
 * `git` invocation of its own — keeps the actual detection logic in
 * scripts/lib/docChecks.ts testable without touching git.
 */

export interface DiffFile {
  path: string;
  addedLines: string[];
}

function git(args: string[]): string {
  return execFileSync("git", args, {
    encoding: "utf-8",
    maxBuffer: 1024 * 1024 * 64,
  });
}

/**
 * Parses `git diff --unified=0` output into per-file added-line lists.
 * Deliberately ignores removed/context lines — every check here cares
 * about text newly introduced by this commit/range, not what already
 * existed before it (see docChecks.ts for why that distinction matters:
 * a self-contradiction claim only makes sense for text you are *adding*
 * right now, not text quoted from history).
 */
export function parseUnifiedDiff(diffText: string): DiffFile[] {
  const files: DiffFile[] = [];
  let current: DiffFile | null = null;

  for (const line of diffText.split("\n")) {
    const fileMatch = /^\+\+\+ b\/(.+)$/.exec(line);
    if (fileMatch) {
      current = { path: fileMatch[1], addedLines: [] };
      files.push(current);
      continue;
    }
    if (current && line.startsWith("+") && !line.startsWith("+++")) {
      current.addedLines.push(line.slice(1));
    }
  }

  return files;
}

/** Added-line diff of everything currently staged for commit. */
export function getStagedDiff(): DiffFile[] {
  return parseUnifiedDiff(git(["diff", "--cached", "--unified=0"]));
}

/** Paths of every file staged for commit (added, modified, or renamed-to). */
export function getStagedFilePaths(): string[] {
  return git(["diff", "--cached", "--name-only"]).split("\n").filter(Boolean);
}

/** Added-line diff between two refs — used in CI to check a push/PR range. */
export function getRangeDiff(base: string, head: string): DiffFile[] {
  return parseUnifiedDiff(git(["diff", `${base}..${head}`, "--unified=0"]));
}

/** Paths touched anywhere in a ref range. */
export function getRangeFilePaths(base: string, head: string): string[] {
  return git(["diff", `${base}..${head}`, "--name-only"])
    .split("\n")
    .filter(Boolean);
}

/**
 * Every commit message in a ref range, concatenated with a blank line
 * between each. CI checks the whole push/PR range as one unit rather than
 * per-commit — this project's own convention is one commit per sprint/
 * feature (confirmed across Sprints 01-16's history), so this is a
 * reasonable simplification, not a full per-commit replay of what the
 * local hooks did.
 */
export function getRangeCommitMessages(base: string, head: string): string {
  return git(["log", `${base}..${head}`, "--format=%B%n---END---"]);
}

/** The message of the commit currently being made (commit-msg hook context). */
export function readCommitMessageFile(path: string): string {
  return readFileSync(path, "utf-8");
}
