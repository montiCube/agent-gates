import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "check_governance.py"

# Built from parts so this file never holds the literal marker.
MARKER = "[ASSUMPTION " + "—" + " verify]"


def entry(number, title="A decision", superseded_by=None, decision="The service does X."):
    lines = [f"# LL-{number:03d}. {title}", ""]
    if superseded_by:
        lines += [f"Superseded by {superseded_by} on 2026-11-24.", ""]
    lines += [
        "**Date.** 2026-11-24.",
        "",
        f"**Decision.** {decision}",
        "",
        "**Reasoning.** Because.",
        "",
        "**Supersedes.** None.",
        "",
        "**Commit.** Lands with the change.",
        "",
    ]
    return "\n".join(lines)


class Repo:
    def __init__(self, root):
        self.root = root
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args):
        proc = subprocess.run(
            ["git", *args], cwd=self.root, capture_output=True, text=True, check=True
        )
        return proc.stdout.strip()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def delete(self, path):
        self.git("rm", "-q", path)

    def digest(self):
        return run_script(self.root, "--write-digest")

    def commit(self, message, *paths):
        self.git("add", "-A", *paths)
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def short(self, sha):
        return self.git("rev-parse", "--short", sha)


def run_script(cwd, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True
    )


def check(repo, base, head="HEAD", markers="fail"):
    return run_script(repo.root, "--base", base, "--head", head, "--markers", markers)


def baseline(tmp_path):
    """A repo with one valid entry, a fresh digest and a service file."""
    repo = Repo(tmp_path)
    repo.write("ledger/LL-001.md", entry(1))
    repo.write("example/service/app.py", "x = 1\n")
    repo.write("example/service/tests/test_app.py", "def test_x():\n    pass\n")
    repo.write("docs/notes.md", "Notes.\n")
    repo.digest()
    base = repo.commit("baseline")
    return repo, base


def test_test_only_commit_with_no_entry_passes(tmp_path):
    repo, base = baseline(tmp_path)
    repo.write("example/service/tests/test_app.py", "def test_y():\n    pass\n")
    repo.commit("add a test")
    result = check(repo, base)
    assert result.returncode == 0, result.stdout
    assert "FAIL" not in result.stdout


def test_behavioural_commit_with_no_entry_fails_and_names_commit_and_files(tmp_path):
    repo, base = baseline(tmp_path)
    repo.write("example/service/app.py", "x = 2\n")
    repo.write(".github/workflows/ci.yml", "name: ci\n")
    sha = repo.commit("change behaviour")
    result = check(repo, base)
    assert result.returncode == 1
    line = next(l for l in result.stdout.splitlines() if "same commit" in l)
    assert repo.short(sha) in line
    assert ".github/workflows/ci.yml, example/service/app.py" in line
    assert "last paragraph" in line


def test_behavioural_commit_that_adds_its_entry_passes(tmp_path):
    repo, base = baseline(tmp_path)
    repo.write("example/service/app.py", "x = 2\n")
    repo.write("ledger/LL-002.md", entry(2))
    repo.digest()
    repo.commit("change behaviour with its entry")
    result = check(repo, base)
    assert result.returncode == 0, result.stdout


def test_entry_in_a_later_commit_of_the_range_fails(tmp_path):
    repo, base = baseline(tmp_path)
    repo.write("example/service/app.py", "x = 2\n")
    first = repo.commit("change behaviour")
    repo.write("ledger/LL-002.md", entry(2))
    repo.digest()
    repo.commit("add the entry afterwards")
    result = check(repo, base)
    assert result.returncode == 1
    assert f"same commit: {repo.short(first)}" in result.stdout


def test_ledger_exempt_counts_only_as_a_trailer_with_a_reason(tmp_path):
    repo, base = baseline(tmp_path)
    repo.write("example/service/app.py", "x = 1  # renamed nothing\n")
    repo.commit("refactor\n\nSame behaviour.\n\nLedger-Exempt: comment only, identical behaviour")
    assert check(repo, base).returncode == 0

    empty_base = repo.git("rev-parse", "HEAD")
    repo.write("example/service/app.py", "x = 1  # again\n")
    repo.commit("refactor\n\nLedger-Exempt:")
    assert check(repo, empty_base).returncode == 1

    body_base = repo.git("rev-parse", "HEAD")
    repo.write("example/service/app.py", "x = 1  # once more\n")
    repo.commit(
        "refactor\n\nLedger-Exempt: comment only, identical behaviour\n\n"
        "This paragraph comes last, so the line above is not a trailer."
    )
    result = check(repo, body_base)
    assert result.returncode == 1
    assert "same commit" in result.stdout


def test_open_marker_fails_on_fail_and_warns_on_warn(tmp_path):
    repo, base = baseline(tmp_path)
    repo.write("docs/notes.md", f"Notes.\n\nThe table went live. {MARKER}\n")
    repo.commit("add a claim")
    failed = check(repo, base, markers="fail")
    assert failed.returncode == 1
    assert "FAIL open marker: docs/notes.md:3" in failed.stdout
    warned = check(repo, base, markers="warn")
    assert warned.returncode == 0
    assert "WARN open marker: docs/notes.md:3" in warned.stdout


def test_backticks_and_fences_are_mentions_and_a_blockquote_is_not(tmp_path):
    repo, base = baseline(tmp_path)
    repo.write(
        "docs/notes.md",
        f"Mark it `{MARKER}` inline.\n\n```\n{MARKER}\n```\n\n~~~~\n{MARKER}\n~~~~\n",
    )
    repo.commit("mentions only")
    assert check(repo, base).returncode == 0

    quote_base = repo.git("rev-parse", "HEAD")
    repo.write("docs/quote.md", f"> The table went live. {MARKER}\n\n> ```\n> {MARKER}\n> ```\n")
    repo.commit("a blockquote")
    result = check(repo, quote_base)
    assert result.returncode == 1
    assert "docs/quote.md:1" in result.stdout
    assert "docs/quote.md:4" in result.stdout


def test_marker_in_an_unchanged_file_is_not_reported(tmp_path):
    repo = Repo(tmp_path)
    repo.write("ledger/LL-001.md", entry(1))
    repo.write("docs/old.md", f"Old claim. {MARKER}\n")
    repo.digest()
    base = repo.commit("baseline with an open marker")
    repo.write("docs/new.md", "New text.\n")
    repo.commit("touch another file")
    result = check(repo, base)
    assert result.returncode == 0, result.stdout
    assert "docs/old.md" not in result.stdout


def test_digest_must_be_regenerated_not_edited(tmp_path):
    repo, base = baseline(tmp_path)
    repo.write("ledger/DIGEST.md", "LL-001 | live | A different title\n")
    repo.commit("alter a digest line")
    altered = check(repo, base)
    assert altered.returncode == 1
    assert "--write-digest" in altered.stdout

    repo.write("ledger/DIGEST.md", "")
    repo.commit("delete the digest line")
    assert check(repo, base).returncode == 1

    repo.digest()
    repo.commit("regenerate the digest")
    assert check(repo, base).returncode == 0


def test_missing_field_and_mismatched_title_number_fail(tmp_path):
    repo, base = baseline(tmp_path)
    repo.write("ledger/LL-002.md", entry(2).replace("**Reasoning.** Because.\n", ""))
    repo.write("ledger/LL-003.md", entry(4))
    repo.digest()
    repo.commit("two broken entries")
    result = check(repo, base)
    assert result.returncode == 1
    assert "ledger/LL-002.md has no '**Reasoning.**' field" in result.stdout
    assert "ledger/LL-003.md:1 title says LL-004 but the file is LL-003" in result.stdout


def test_entries_are_never_deleted_or_rewritten_only_superseded(tmp_path):
    repo, base = baseline(tmp_path)
    repo.write("ledger/LL-002.md", entry(2, decision="The service does Z."))
    repo.write("ledger/LL-001.md", entry(1, superseded_by="LL-002"))
    repo.digest()
    repo.commit("supersede LL-001")
    assert check(repo, base).returncode == 0

    edit_base = repo.git("rev-parse", "HEAD")
    repo.write("ledger/LL-001.md", entry(1, superseded_by="LL-002", decision="The service does Y."))
    repo.commit("rewrite a decision")
    edited = check(repo, edit_base)
    assert edited.returncode == 1
    assert "never rewrite" in edited.stdout

    delete_base = repo.git("rev-parse", "HEAD")
    repo.delete("ledger/LL-001.md")
    repo.digest()
    repo.commit("delete an entry")
    deleted = check(repo, delete_base)
    assert deleted.returncode == 1
    assert "never delete" in deleted.stdout


def test_new_entry_numbered_below_an_existing_one_fails(tmp_path):
    repo, _ = baseline(tmp_path)
    repo.write("ledger/LL-005.md", entry(5))
    repo.digest()
    base = repo.commit("a gap is fine")
    repo.write("ledger/LL-003.md", entry(3))
    repo.digest()
    repo.commit("take a lower number")
    result = check(repo, base)
    assert result.returncode == 1
    assert "adds ledger/LL-003.md but LL-005 already exists" in result.stdout


def test_merge_commit_in_the_range_is_skipped(tmp_path):
    repo, base = baseline(tmp_path)
    repo.git("checkout", "-q", "-b", "side")
    repo.write("docs/side.md", "Side.\n")
    repo.commit("side work")
    repo.git("checkout", "-q", "main")
    repo.write("docs/main.md", "Main.\n")
    repo.commit("main work")
    # A merge that also changes behaviour: judged, it would fail.
    repo.git("merge", "-q", "--no-ff", "--no-commit", "side")
    repo.write("example/service/app.py", "x = 3\n")
    repo.commit("merge side")
    result = check(repo, base)
    assert result.returncode == 0, result.stdout
    assert "checked 2 commit(s)" in result.stdout


def test_this_repository_passes_structure_and_digest_at_head(tmp_path):
    result = run_script(REPO, "--base", "HEAD", "--head", "HEAD", "--markers", "fail")
    assert result.returncode == 0, result.stdout
    assert "FAIL" not in result.stdout


def test_non_ascii_file_names_are_read_unquoted(tmp_path):
    # LL-005: git quotes non-ASCII paths unless core.quotepath is off.
    repo, base = baseline(tmp_path)
    repo.write("tools/café.py", "x = 1\n")
    sha = repo.commit("add a behaviour file with a non-ASCII name")
    behaviour = check(repo, base)
    assert behaviour.returncode == 1
    assert f"same commit: {repo.short(sha)} changes behaviour (tools/café.py)" in behaviour.stdout

    marker_base = repo.git("rev-parse", "HEAD")
    repo.write("docs/café.md", f"The table went live. {MARKER}\n")
    repo.commit("an open marker in a non-ASCII file name")
    marker = check(repo, marker_base)
    assert marker.returncode == 1
    assert "FAIL open marker: docs/café.md:1" in marker.stdout
