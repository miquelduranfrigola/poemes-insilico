#!/usr/bin/env node
/**
 * sillabes.js — Catalan syllable counter for IUPAC molecule names.
 *
 * Reproduces https://www.softcatala.org/sillabes/ exactly by running Softcatala's
 * own (unmodified) JavaScript headlessly. The browser code in vendor/softcatala/
 * relies on globals (`document`, `console`) and runs `onChangeFunction()` at load,
 * so we evaluate it inside a Node `vm` sandbox that supplies a fake `document` and
 * a quiet `console`. We then reproduce the tool's per-line pipeline:
 *
 *     getResultLine( hyphenate(text).adjustHyphenatedText() )
 *
 * For each input line the tool computes three syllable counts:
 *   - graphic  : written syllables.
 *   - phonetic : with elisions and synalepha (sinalefa) across words, marked '‿'.
 *   - poetic   : counted up to the last stressed syllable (Catalan verse metre).
 *                Two variants: poetic1 (graphic-based) and poetic2 (phonetic-based
 *                + a final synalepha adjustment). poetic1 is what the site shows;
 *                poetic2 is shown in parentheses when it differs.
 *
 * Usage:
 *   node code/sillabes.js "propan-2-ol" "àcid acètic"     # one name per argument
 *   printf 'metà\npropanol\n' | node code/sillabes.js      # one name per stdin line
 *   node code/sillabes.js --json "metà" "età"              # machine-readable output
 *
 * Options:
 *   --json     Emit a JSON array (one object per input line) instead of a table.
 *   --debug    Forward Softcatala's internal hyphenation logging to stderr.
 *   -h,--help  Show this help.
 *
 * Note on numbers/locants: digits (e.g. the "2" in "propan-2-ol") are treated as
 * word separators, not pronounced — matching the web tool. Spell out locants if
 * you want them counted as syllables.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const VENDOR = path.join(__dirname, "vendor", "softcatala");
const VENDOR_FILES = ["ca.js", "hyphen.js", "hyphen-softcatala.js"];

/**
 * Build a sandbox, load the unmodified Softcatala scripts into it, and expose a
 * single `processLine(line)` entry point that runs inside the sandbox realm (so
 * the String.prototype helpers the vendored code installs are available).
 * @param {boolean} debug forward internal hyphenation logs to stderr
 * @returns {(line: string) => object} per-line analyser
 */
function buildAnalyser(debug) {
  // A minimal DOM so the vendored `onChangeFunction()` runs harmlessly at load.
  const stubEl = { value: "", innerHTML: "", style: {} };
  const sandbox = {
    console: {
      log: debug ? (...a) => process.stderr.write(a.join(" ") + "\n") : () => {},
      warn: (...a) => process.stderr.write(a.join(" ") + "\n"),
      error: (...a) => process.stderr.write(a.join(" ") + "\n"),
    },
    document: { getElementById: () => stubEl },
  };
  vm.createContext(sandbox);

  for (const file of VENDOR_FILES) {
    const src = fs.readFileSync(path.join(VENDOR, file), "utf8");
    vm.runInContext(src, sandbox, { filename: file });
  }

  // Glue authored here (NOT part of the vendored code): reproduce the web tool's
  // single-line pipeline and return a plain data object. Runs in the sandbox realm.
  const glue = `
    this.__processLine = function (rawLine) {
      var original = normalizeNFC(String(rawLine)).replace(/\\r/g, "").trim().replace(/_/g, " ");
      if (original === "" || original.lineCount() < 1) {
        return { input: rawLine, empty: true };
      }
      var hyph = hyphenate(original).adjustHyphenatedText();
      var r = getResultLine(hyph);
      var amb = checkAmbiguities(original);
      return {
        input: rawLine,
        empty: false,
        graphic: r.count_graphical,
        phonetic: r.count_phonetical,
        poetic1: r.count_poetical1,
        poetic2: r.count_poetical2,
        numwords: r.numwords,
        hyphenated: hyph,               // graphic syllabification, '_' between syllables
        phonetic_line: r.hyphenated_line, // phonetic view (HTML-massaged, keeps '‿')
        ambiguity_count: amb.count,
        ambiguity_html: amb.hints
      };
    };
  `;
  vm.runInContext(glue, sandbox, { filename: "glue.js" });
  return sandbox.__processLine;
}

/** Turn Softcatala's '_'-separated graphic output into a readable "pro·pan·ol". */
function displaySyllables(hyphenated) {
  return hyphenated.replace(/_/g, "·");
}

/** Turn the phonetic HTML line into plain text: '|'→'·', '&nbsp; '→' ', keep '‿'. */
function displayPhonetic(phoneticLine) {
  return phoneticLine.replace(/&nbsp; /g, " ").replace(/\|/g, "·");
}

/** Strip the <li>…</li> ambiguity hints down to plain lines. */
function ambiguityLines(html) {
  return html
    .replace(/<\/li>/g, "\n")
    .replace(/<[^>]+>/g, "")
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

function poeticDisplay(p1, p2) {
  return p1 === p2 ? String(p1) : `${p1} (${p2})`;
}

function printHelp() {
  const header = fs.readFileSync(__filename, "utf8");
  // Print the top doc comment as help text.
  const match = header.match(/\/\*\*([\s\S]*?)\*\//);
  const body = match
    ? match[1]
        .split("\n")
        .map((l) => l.replace(/^\s*\*?\s?/, ""))
        .join("\n")
        .trim()
    : "sillabes.js — Catalan syllable counter";
  process.stdout.write(body + "\n");
}

function readStdinLines() {
  let data = "";
  try {
    data = fs.readFileSync(0, "utf8");
  } catch (_) {
    data = "";
  }
  return data.split(/\r?\n/).filter((l) => l.trim() !== "");
}

function main() {
  const argv = process.argv.slice(2);
  const flags = new Set(argv.filter((a) => a.startsWith("-")));
  const names = argv.filter((a) => !a.startsWith("-"));

  if (flags.has("-h") || flags.has("--help")) {
    printHelp();
    return;
  }

  const debug = flags.has("--debug");
  const asJson = flags.has("--json");

  const inputs = names.length > 0 ? names : readStdinLines();
  if (inputs.length === 0) {
    process.stderr.write(
      "No input. Pass names as arguments or pipe them on stdin. See --help.\n"
    );
    process.exitCode = 1;
    return;
  }

  const analyse = buildAnalyser(debug);
  const results = inputs.map((line) => analyse(line));

  if (asJson) {
    process.stdout.write(JSON.stringify(results, null, 2) + "\n");
    return;
  }

  // Human-readable table.
  const rows = results.map((r) =>
    r.empty
      ? { g: "-", f: "-", p: "-", syl: `${r.input}  (buit)` }
      : {
          g: String(r.graphic),
          f: String(r.phonetic),
          p: poeticDisplay(r.poetic1, r.poetic2),
          syl: displaySyllables(r.hyphenated),
        }
  );

  const H = { g: "gràfic", f: "fonètic", p: "poètic", syl: "síl·labes" };
  const w = {
    g: Math.max(H.g.length, ...rows.map((x) => x.g.length)),
    f: Math.max(H.f.length, ...rows.map((x) => x.f.length)),
    p: Math.max(H.p.length, ...rows.map((x) => x.p.length)),
  };
  const pad = (s, n) => String(s).padStart(n);

  const line = (a, b, c, d) =>
    `${pad(a, w.g)}  ${pad(b, w.f)}  ${pad(c, w.p)}   ${d}`;
  process.stdout.write(line(H.g, H.f, H.p, H.syl) + "\n");
  process.stdout.write(
    line("─".repeat(w.g), "─".repeat(w.f), "─".repeat(w.p), "─".repeat(H.syl.length)) +
      "\n"
  );
  for (const x of rows) process.stdout.write(line(x.g, x.f, x.p, x.syl) + "\n");

  // Ambiguity hints (if any) to stderr so they don't pollute the table.
  const hinted = results.filter((r) => !r.empty && r.ambiguity_count > 0);
  if (hinted.length > 0) {
    process.stderr.write("\nParticions dubtoses:\n");
    for (const r of hinted)
      for (const h of ambiguityLines(r.ambiguity_html))
        process.stderr.write(`  • [${r.input}] ${h}\n`);
  }
}

main();
