"""Fail the build when the repo's ledger, marker or digest rules are broken.

    python tools/check_governance.py --base <rev> --head <rev> --markers fail|warn
    python tools/check_governance.py --write-digest

Run from inside the repository. Every check runs; each failure prints one line
starting with FAIL; the exit code is 1 if any failed. See ledger/LL-004.md.
Standard library only.
"""

import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path

# R2. A commit is behavioural if it changes a file under one of these paths and
# not under one of the exceptions. Widening the list is a code change.
BEHAVIOUR_PATHS = ("example/service/", "tools/", ".github/workflows/")
BEHAVIOUR_EXCEPT = ("example/service/tests/", "tools/tests/")

FIELDS = ("Date", "Decision", "Reasoning", "Supersedes", "Commit")
LEDGER_DIR = "ledger"
DIGEST_PATH = "ledger/DIGEST.md"
EXEMPT_TRAILER = "Ledger-Exempt"

# R7. Built from parts so this file never holds the literal marker.
MARKER = "[ASSUMPTION " + "—" + " verify]"

ENTRY_PATH = re.compile(r"^ledger/LL-(\d{3,})\.md$")
ENTRY_GLOB = re.compile(r"^ledger/LL-[^/]*\.md$")
TITLE = re.compile(r"^# LL-(\d{3,})\. (\S.*)$")
SUPERSEDED = re.compile(r"^Superseded by (LL-\d{3,}) on \d{4}-\d{2}-\d{2}\.$")
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
BLOCKQUOTE = re.compile(r"^ {0,3}>")


class GitError(Exception):
    pass


def git(*args, check=True):
    proc = subprocess.run(["git", *args], capture_output=True)
    if check and proc.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed: {proc.stderr.decode(errors='replace').strip()}"
        )
    return proc


def git_text(*args):
    return git(*args).stdout.decode("utf-8", errors="replace")


def read_blob(rev, path):
    """Bytes of path at rev, or None if it is absent there."""
    proc = git("show", f"{rev}:{path}", check=False)
    return proc.stdout if proc.returncode == 0 else None


def tree_files(rev, prefix):
    out = git_text("ls-tree", "-r", "--name-only", rev, "--", prefix)
    return [line for line in out.splitlines() if line]


def is_behavioural(path):
    return path.startswith(BEHAVIOUR_PATHS) and not path.startswith(BEHAVIOUR_EXCEPT)


def entry_number(path):
    m = ENTRY_PATH.match(path)
    return int(m.group(1)) if m else None


# ----- the ledger and the digest ------------------------------------------


def parse_entry(text):
    """Return (title_number, title, superseded_by) or None if no title line."""
    lines = text.splitlines()
    m = TITLE.match(lines[0]) if lines else None
    if not m:
        return None
    superseded_by = None
    for line in lines:
        s = SUPERSEDED.match(line)
        if s:
            superseded_by = s.group(1)
            break
    return int(m.group(1)), m.group(2).strip(), superseded_by


def load_entries(read, paths):
    """Map path -> text for each ledger entry, given a reader."""
    entries = {}
    for path in sorted(paths):
        if ENTRY_GLOB.match(path):
            data = read(path)
            if data is not None:
                entries[path] = data.decode("utf-8", errors="replace")
    return entries


def render_digest(entries):
    rows = []
    for path, text in entries.items():
        parsed = parse_entry(text)
        number = entry_number(path)
        if parsed is None or number is None:
            continue
        _, title, superseded_by = parsed
        status = f"superseded by {superseded_by}" if superseded_by else "live"
        rows.append((number, f"LL-{number:03d} | {status} | {title}"))
    rows.sort()
    return "".join(line + "\n" for _, line in rows)


def check_structure(entries):
    failures = []
    seen = {}
    for path, text in entries.items():
        number = entry_number(path)
        if number is None:
            failures.append(
                f"ledger structure: {path} is not named LL-NNN.md; rename it to its number"
            )
            continue
        if number in seen:
            failures.append(
                f"ledger structure: {path} and {seen[number]} share number {number}; numbers are unique"
            )
        seen[number] = path
        parsed = parse_entry(text)
        if parsed is None:
            failures.append(
                f"ledger structure: {path}:1 has no title line '# LL-NNN. <title>'; add it"
            )
        elif parsed[0] != number:
            failures.append(
                f"ledger structure: {path}:1 title says LL-{parsed[0]:03d} but the file is "
                f"LL-{number:03d}; make them match"
            )
        lines = text.splitlines()
        for field in FIELDS:
            if not any(line.startswith(f"**{field}.**") for line in lines):
                failures.append(
                    f"ledger structure: {path} has no '**{field}.**' field; add it"
                )
    return failures


def check_digest(head, entries):
    committed = read_blob(head, DIGEST_PATH)
    expected = render_digest(entries)
    if committed is None:
        return [
            f"digest: {DIGEST_PATH} is missing at {short(head)}; run "
            "'python tools/check_governance.py --write-digest' and commit it"
        ]
    if committed.decode("utf-8", errors="replace") != expected:
        return [
            f"digest: {DIGEST_PATH} is stale or hand-edited; run "
            "'python tools/check_governance.py --write-digest' and commit it"
        ]
    return []


# ----- each commit in the range -------------------------------------------


def short(rev):
    return git_text("rev-parse", "--short", rev).strip()


def empty_tree():
    proc = subprocess.run(
        ["git", "hash-object", "-t", "tree", "--stdin"], input=b"", capture_output=True
    )
    return proc.stdout.decode().strip()


def changes(parent, sha):
    """List of (status, path) between parent and sha, renames split."""
    out = git_text("diff", "--name-status", "--no-renames", parent, sha)
    result = []
    for line in out.splitlines():
        if not line:
            continue
        status, path = line.split("\t", 1)
        result.append((status[0], path))
    return result


def exempt_reason(sha):
    # R4. Read as a trailer through git, never by searching the message.
    fmt = f"%(trailers:key={EXEMPT_TRAILER},valueonly)"
    return git_text("log", "-1", f"--format={fmt}", sha).strip()


def only_superseded_added(old, new):
    """R5. True if new is old plus one Superseded line and blank lines only."""
    a = old.splitlines(keepends=True)
    b = new.splitlines(keepends=True)
    added = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag != "insert":
            return False
        added.extend(b[j1:j2])
    if not added or any(not line.endswith("\n") for line in added):
        return False
    stripped = [line.rstrip("\n") for line in added]
    superseded = [line for line in stripped if SUPERSEDED.match(line)]
    others = [line for line in stripped if not SUPERSEDED.match(line)]
    return len(superseded) == 1 and all(line.strip() == "" for line in others)


def check_commit(sha):
    failures = []
    tag = short(sha)
    parents = git_text("rev-list", "--parents", "-n", "1", sha).split()[1:]
    parent = parents[0] if parents else empty_tree()
    changed = changes(parent, sha)

    added_entries = [p for s, p in changed if s == "A" and ENTRY_PATH.match(p)]

    # R2, R3, R4. A behavioural commit adds its own entry.
    behaviour = sorted({p for _, p in changed if is_behavioural(p)})
    if behaviour and not added_entries:
        if not exempt_reason(sha):
            failures.append(
                f"same commit: {tag} changes behaviour ({', '.join(behaviour)}) but adds no "
                f"new ledger/LL-NNN.md; add the entry in this same commit, or, for a refactor "
                f"with identical behaviour, end the message with a '{EXEMPT_TRAILER}: <reason>' "
                f"trailer (git reads trailers only in the message's last paragraph)"
            )

    # R5. Never deleted, renamed or rewritten.
    for status, path in changed:
        if not ENTRY_GLOB.match(path) or status == "A":
            continue
        if status == "D":
            failures.append(
                f"never delete: {tag} deletes or renames {path}; entries are never deleted, "
                f"renamed or rewritten, so restore it and supersede it with a new entry"
            )
            continue
        old = read_blob(parent, path) or b""
        new = read_blob(sha, path) or b""
        if not only_superseded_added(
            old.decode("utf-8", errors="replace"), new.decode("utf-8", errors="replace")
        ):
            failures.append(
                f"never rewrite: {tag} edits {path}; the only change allowed to an entry is "
                f"one added line 'Superseded by LL-NNN on YYYY-MM-DD.', so revert the edit "
                f"and record the change as a new entry"
            )

    # R6. Numbers only go up.
    if added_entries:
        before = [entry_number(p) for p in tree_files(parent, LEDGER_DIR)]
        before = [n for n in before if n is not None]
        highest = max(before, default=0)
        for path in added_entries:
            number = entry_number(path)
            if number <= highest:
                failures.append(
                    f"numbers: {tag} adds {path} but LL-{highest:03d} already exists in its "
                    f"parent; take a number above LL-{highest:03d}"
                )
    return failures


# ----- open markers --------------------------------------------------------


def strip_code_spans(line):
    """Remove inline code spans: a run of N backticks closes on the next run of N."""
    out = []
    i = 0
    n = len(line)
    while i < n:
        if line[i] != "`":
            out.append(line[i])
            i += 1
            continue
        j = i
        while j < n and line[j] == "`":
            j += 1
        run = j - i
        k = j
        close = -1
        while k < n:
            if line[k] == "`":
                m = k
                while m < n and line[m] == "`":
                    m += 1
                if m - k == run:
                    close = k
                    break
                k = m
            else:
                k += 1
        if close < 0:
            out.append(line[i:j])
            i = j
        else:
            i = close + run
    return "".join(out)


def open_markers(text):
    """Line numbers holding an open marker under R7."""
    found = []
    fence = None
    for number, line in enumerate(text.splitlines(), start=1):
        if fence is not None:
            stripped = line.lstrip(" ")
            if len(line) - len(stripped) <= 3 and stripped.startswith(fence):
                rest = stripped[len(fence):]
                rest = rest.lstrip(fence[0])
                if rest.strip() == "":
                    fence = None
            continue
        if not BLOCKQUOTE.match(line):
            m = FENCE_OPEN.match(line)
            if m:
                fence = m.group(1)
                continue
        if MARKER in strip_code_spans(line):
            found.append(number)
    return found


def check_markers(base, head):
    findings = []
    out = git_text("diff", "--name-only", "--no-renames", "--diff-filter=d", f"{base}...{head}")
    for path in sorted(line for line in out.splitlines() if line):
        data = read_blob(head, path)
        if data is None:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for number in open_markers(text):
            findings.append(
                f"open marker: {path}:{number} has an open {MARKER}; verify the claim and "
                f"cite the source, or delete the claim (backticks or a fenced block make it a mention)"
            )
    return findings


# ----- entry points --------------------------------------------------------


def run_checks(base, head, markers):
    for rev in (base, head):
        if git("rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}", check=False).returncode:
            print(f"FAIL setup: {rev} is not a commit in this clone; fetch it or pass another rev")
            return 1

    failures = []
    entries = load_entries(lambda p: read_blob(head, p), tree_files(head, LEDGER_DIR))
    failures += check_structure(entries)
    failures += check_digest(head, entries)

    shas = git_text("rev-list", "--no-merges", "--reverse", f"{base}..{head}").split()
    for sha in shas:
        failures += check_commit(sha)

    marker_findings = check_markers(base, head)
    if markers == "fail":
        failures += marker_findings
    else:
        for line in marker_findings:
            print(f"WARN {line}")

    for line in failures:
        print(f"FAIL {line}")
    print(
        f"checked {len(shas)} commit(s) in {short(base)}..{short(head)}, "
        f"{len(entries)} entries; {len(failures)} failure(s)"
    )
    return 1 if failures else 0


def write_digest():
    root = Path(git_text("rev-parse", "--show-toplevel").strip())
    ledger = root / LEDGER_DIR
    paths = [f"{LEDGER_DIR}/{p.name}" for p in ledger.glob("LL-*.md")]
    entries = load_entries(lambda p: (root / p).read_bytes(), paths)
    (root / DIGEST_PATH).write_text(render_digest(entries), encoding="utf-8")
    print(f"wrote {DIGEST_PATH}, {len(entries)} entries")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--markers", choices=("fail", "warn"), default="fail")
    parser.add_argument("--write-digest", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.write_digest:
            return write_digest()
        if not args.base or not args.head:
            parser.error("--base and --head are required unless --write-digest is given")
        return run_checks(args.base, args.head, args.markers)
    except GitError as exc:
        print(f"FAIL setup: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
