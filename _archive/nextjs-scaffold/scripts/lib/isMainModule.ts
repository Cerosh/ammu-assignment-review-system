import { pathToFileURL } from "node:url";

/**
 * True when this module was executed directly (`tsx scripts/x.ts`) rather
 * than imported (e.g. by a test). Comparing `import.meta.url` against a
 * raw `file://${process.argv[1]}` string breaks whenever the path contains
 * spaces or other characters `file://` URLs must percent-encode — a repo
 * checked out under a path with spaces is exactly such a case.
 * `pathToFileURL` encodes correctly before comparing.
 */
export function isMainModule(moduleUrl: string): boolean {
  return process.argv[1] !== undefined && moduleUrl === pathToFileURL(process.argv[1]).href;
}
