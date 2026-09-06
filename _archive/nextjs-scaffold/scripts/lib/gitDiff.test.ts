import { describe, expect, it } from "vitest";
import { parseUnifiedDiff } from "./gitDiff";

describe("parseUnifiedDiff", () => {
  it("extracts only added lines, grouped per file", () => {
    const diffText = [
      "diff --git a/README.md b/README.md",
      "index 1234567..89abcde 100644",
      "--- a/README.md",
      "+++ b/README.md",
      "@@ -5,1 +5,2 @@",
      "-Old line",
      "+New line one",
      "+New line two",
      "diff --git a/package.json b/package.json",
      "index 1111111..2222222 100644",
      "--- a/package.json",
      "+++ b/package.json",
      "@@ -1,1 +1,1 @@",
      '-  "version": "0.1.0",',
      '+  "version": "0.2.0",',
    ].join("\n");

    const files = parseUnifiedDiff(diffText);

    expect(files).toHaveLength(2);
    expect(files[0]).toEqual({
      path: "README.md",
      addedLines: ["New line one", "New line two"],
    });
    expect(files[1]).toEqual({
      path: "package.json",
      addedLines: ['  "version": "0.2.0",'],
    });
  });

  it("returns an empty array for an empty diff", () => {
    expect(parseUnifiedDiff("")).toEqual([]);
  });

  it("ignores the +++ file header line itself as an added line", () => {
    const diffText = [
      "diff --git a/x.md b/x.md",
      "--- a/x.md",
      "+++ b/x.md",
      "@@ -1 +1 @@",
      "+hello",
    ].join("\n");
    const files = parseUnifiedDiff(diffText);
    expect(files).toHaveLength(1);
    expect(files[0].addedLines).toEqual(["hello"]);
  });

  it("handles a newly-created file (no --- a/ line)", () => {
    const diffText = [
      "diff --git a/new.md b/new.md",
      "new file mode 100644",
      "index 0000000..1111111",
      "--- /dev/null",
      "+++ b/new.md",
      "@@ -0,0 +1,2 @@",
      "+line one",
      "+line two",
    ].join("\n");
    const files = parseUnifiedDiff(diffText);
    expect(files).toEqual([{ path: "new.md", addedLines: ["line one", "line two"] }]);
  });
});
