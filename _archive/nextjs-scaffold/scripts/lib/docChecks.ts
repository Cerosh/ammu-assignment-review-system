import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import type { DiffFile } from "./gitDiff";

/**
 * Pure detection logic for the four doc-staleness guardrails. Deliberately
 * git-free — every function here takes already-parsed diff data or file
 * contents, so it's testable with plain fixtures and reusable identically
 * from a pre-commit hook, a commit-msg hook, or CI.
 */

export interface Finding {
  file: string;
  line?: string;
  message: string;
}

/**
 * Commit trailer that explicitly defers a doc-contact/freshness requirement,
 * visible in `git log` rather than a silent `--no-verify` bypass — matches
 * this project's established "disclose rather than silently skip"
 * convention (e.g. the Sentry deferral, the Rich Results Test disclosure).
 */
const DOCS_DEFERRED_TRAILER = /^Docs-Deferred:\s*(.+)$/im;

export function getDocsDeferredReason(commitMessage: string): string | null {
  const match = DOCS_DEFERRED_TRAILER.exec(commitMessage);
  return match ? match[1].trim() : null;
}

// ---------------------------------------------------------------------------
// Check 1 — self-contradiction
// ---------------------------------------------------------------------------

/**
 * Phrases that are false by construction the moment they appear in a
 * commit's own added lines — if a file being committed right now says
 * "not yet committed", that claim is already wrong.
 *
 * Deliberately scoped to deployment/commit-status phrasing only — NOT a
 * general "(Future)" or "not yet started" detector, which would false-
 * positive on genuinely-still-future statements (a doc's own planned scope,
 * ARCHITECTURE.md's "Database (Future)", etc.) that have nothing to do with
 * the commit being made.
 */
const SELF_CONTRADICTION_PATTERNS: RegExp[] = [
  /not yet committed/i,
  /not yet deployed/i,
  /not yet pushed/i,
  /not yet connected to (vercel|production)/i,
  /commit\s*\/\s*push\s*\/\s*deploy.{0,60}remain(s|ing)? open/i,
  /committing,?\s*pushing,?\s*and\s*deploying.{0,40}remain/i,
];

/**
 * Files where these patterns are expected to appear as source text, not as
 * a live status claim: the guardrail scripts themselves (the pattern list
 * literally contains these phrases) and their tests (fixtures exercising
 * true-positive cases). Found the hard way — the first real run of this
 * check against a staged commit flagged its own source file and test
 * fixtures, since `/not yet committed/i,` is, syntactically, a line
 * containing "not yet committed".
 */
function isExemptFromSelfContradictionCheck(path: string): boolean {
  return path.startsWith("scripts/") && (path.endsWith(".ts") || path.endsWith(".tsx"));
}

export function findSelfContradictions(files: DiffFile[]): Finding[] {
  const findings: Finding[] = [];

  for (const file of files) {
    if (isExemptFromSelfContradictionCheck(file.path)) continue;
    for (const line of file.addedLines) {
      for (const pattern of SELF_CONTRADICTION_PATTERNS) {
        if (pattern.test(line)) {
          findings.push({
            file: file.path,
            line: line.trim(),
            message: `contains a self-contradiction — this text claims something "not yet" done, but it is being committed right now (matched ${pattern})`,
          });
          break; // one finding per line is enough, even if multiple patterns match
        }
      }
    }
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Check 2 — zero doc contact
// ---------------------------------------------------------------------------

const SPRINT_REFERENCE = /Sprint\s+(\d{1,2})([a-z]?)\b/i;
const CODE_DIRS = ["app/", "components/", "features/", "lib/"];

export interface DocContactFinding {
  sprintNumber: string;
  expectedGlob: string;
}

/**
 * If the commit message references a sprint (this project's own convention,
 * e.g. "Sprint 11", "Sprint 09b", "Sprint 15, F-010") and the diff touches
 * application code, at least one file under that sprint's own
 * `sprints/sprint-{NN}{suffix}-` (wildcard) folder must also be part of the diff
 * — guards against implementation commits that touch zero files in the
 * sprint's own docs, leaving README/tasks.md unrevisited after being written
 * as pre-sprint templates. Only meaningful once commit messages consistently
 * include a "(Sprint NN)" reference — it can't retroactively flag commits
 * made before that convention existed.
 */
export function findMissingSprintDocContact(
  commitMessage: string,
  touchedPaths: string[],
): DocContactFinding | null {
  const match = SPRINT_REFERENCE.exec(commitMessage);
  if (!match) return null;

  const touchesCode = touchedPaths.some((path) => CODE_DIRS.some((dir) => path.startsWith(dir)));
  if (!touchesCode) return null;

  const [, number, suffix] = match;
  const paddedNumber = number.padStart(2, "0");
  const sprintPrefix = `sprints/sprint-${paddedNumber}${suffix.toLowerCase()}-`;
  const touchesSprintDocs = touchedPaths.some((path) => path.startsWith(sprintPrefix));

  if (touchesSprintDocs) return null;

  return {
    sprintNumber: `${paddedNumber}${suffix}`,
    expectedGlob: `${sprintPrefix}*/README.md (or tasks.md, etc.)`,
  };
}

// ---------------------------------------------------------------------------
// Check 3 — internal consistency (Features table vs. tasks.md checkboxes)
// ---------------------------------------------------------------------------

const FEATURES_TABLE_ROW = /^\|\s*F-\d+\s*\|[^|]*\|[^|]*\|\s*([^|]+?)\s*\|$/gm;
const UNCHECKED_TASK_LINE = /^-\s*\[\s\]/;

export interface ConsistencyFinding {
  sprintDir: string;
  unchecked: string[];
}

/**
 * If every Feature row in a sprint's README.md is the exact plain word
 * "Completed" (not a compound status like "Completed (automated proxy...)"
 * or "Deferred — ..." — those are nuanced, deliberate, and shouldn't
 * trigger this), tasks.md for that same sprint must have zero remaining
 * `- [ ]` lines — guards against a README.md that's accurate while tasks.md
 * still has stale unchecked boxes nobody went back to flip.
 */
export function checkSprintConsistency(readmeText: string, tasksText: string | null): string[] {
  const statuses = [...readmeText.matchAll(FEATURES_TABLE_ROW)].map((m) => m[1].trim());
  if (statuses.length === 0) return [];

  const allPlainCompleted = statuses.every((status) => status === "Completed");
  if (!allPlainCompleted) return [];
  if (tasksText === null) return [];

  return tasksText.split("\n").filter((line) => UNCHECKED_TASK_LINE.test(line.trim()));
}

/** Runs `checkSprintConsistency` across every `sprints/sprint-` (wildcard) folder. */
export function findSprintConsistencyIssues(sprintsDir: string): ConsistencyFinding[] {
  const findings: ConsistencyFinding[] = [];
  let entries: import("node:fs").Dirent[];
  try {
    entries = readdirSync(sprintsDir, { withFileTypes: true }).filter((e) => e.isDirectory());
  } catch {
    return findings; // no sprints/ directory yet — nothing to check
  }

  for (const entry of entries) {
    const readmePath = join(sprintsDir, entry.name, "README.md");
    const tasksPath = join(sprintsDir, entry.name, "tasks.md");
    let readmeText: string;
    try {
      readmeText = readFileSync(readmePath, "utf-8");
    } catch {
      continue; // no README.md — nothing to check
    }
    let tasksText: string | null;
    try {
      tasksText = readFileSync(tasksPath, "utf-8");
    } catch {
      tasksText = null; // no tasks.md for this sprint — nothing to cross-check
    }

    const unchecked = checkSprintConsistency(readmeText, tasksText);
    if (unchecked.length > 0) {
      findings.push({ sprintDir: entry.name, unchecked });
    }
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Check 4 — top-level .ai/ freshness on sprint closeout
// ---------------------------------------------------------------------------

const SPRINT_CLOSEOUT_LINE = /^Sprint Status:.*(Complete|Deployed|✅)/im;
const SPRINT_README_PATH = /^sprints\/sprint-[^/]+\/README\.md$/;

export interface FreshnessFinding {
  file: string;
}

/**
 * If this commit adds a "Sprint Status: ...Complete/Deployed/✅" line to a
 * sprint's own README.md — the exact moment a sprint closes out — the
 * top-level `.ai/CONTEXT.md` must also be part of the same commit, so it
 * doesn't drift out of sync with what's actually shipped.
 *
 * Deliberately narrow: only fires on this specific structural event, not a
 * general "time since CONTEXT.md was last touched" heuristic, which would
 * false-positive on routine ongoing commits that have nothing to do with a
 * sprint closing out.
 */
export function findMissingContextUpdate(
  files: DiffFile[],
  touchedPaths: string[],
): FreshnessFinding | null {
  const closeoutFile = files.find(
    (file) =>
      SPRINT_README_PATH.test(file.path) &&
      file.addedLines.some((line) => SPRINT_CLOSEOUT_LINE.test(line)),
  );
  if (!closeoutFile) return null;
  if (touchedPaths.includes(".ai/CONTEXT.md")) return null;

  return { file: closeoutFile.path };
}
