# Logic ledger

An agent starts each session with no memory of the last one. Another agent may be working the same code at the same time. The code says what the system does. The ledger says why, and what it replaced.

The ledger is shared memory across agent instances and across time. When behaviour surprises you, start here.

## Entry format

One file per entry, in `ledger/`, named `LL-NNN.md`. Numbers are never reused and never renumbered.

Each entry has these fields:

- **LL-NNN and title.** The title states the decision as a sentence.
- **Date.** The day the entry lands.
- **Decision.** What the system now does. Names and numbers, not adjectives.
- **Reasoning.** Why. What was wrong before, or what was weighed.
- **Supersedes.** The entry this replaces, in whole or in part. Or none.
- **Commit.** Where the change lands.

A commit cannot contain its own hash. So the Commit field names the files the change touches, and git supplies the hash:

```
git log -1 --format=%H -- ledger/LL-003.md
```

## The same-commit rule

A behavioural change and its ledger entry are one commit.

History that can drift from code is worse than no history. An entry written a week later records what someone remembers. An entry in the same commit records what the diff does. A reviewer reads both at once. If the change is reverted, the entry goes with it.

A change is behavioural if it changes what the system does with an input: what it acts on, how much, when it holds, what it reports. A refactor with identical behaviour, a docs edit or a new test on its own needs no entry. If unsure, write one.

## Never delete

An entry is never deleted and never rewritten. When a later entry replaces it, the old entry gets one dated line under its title:

```
Superseded by LL-002 on 2026-09-24.
```

A correction is a new entry too. It quotes the claim that was wrong, says how the error was found, and says what changed.

## Reading a large ledger

The source ledger has 248 entries in about 300 KB. That does not fit in a session's context. Keep a one-line digest, generated from the entries, not written by hand. Agents read the digest at the start of a session and open a full entry only when they cite it. Run a check in the test suite: numbers unique and increasing, every field present, the digest fresh.

## Two incidents from the source system

**Entries that lived only in commit messages.** 14 decisions existed only in commit subjects. They were never written into the ledger. An agent reading the ledger could not see them. On reconciliation they were folded in, and every entry was checked against the code and given a status flag.

**A section dropped by an unrelated commit.** A behavioural fix also rewrote the ledger's tail and dropped a whole section: 5 entries that live code still cited. It stayed missing for just over 3 months. The section was restored verbatim from the last commit that had it, with a dated note saying why.

Both are drift between the record and the code. The same-commit rule turns the first into a visible violation in review. A reviewer who reads the ledger diff in every pull request catches the second.

## The samples

- `ledger/LL-001.md`. A decision. Anonymised from the source system.
- `ledger/LL-002.md`. A reversal of LL-001. Anonymised from the source system.
- `ledger/LL-003.md`. A correction. This repo's own. It lands in the example pull request, in the same commit as the change to `example/service/app.py`.

The example service's first commit implements a reduced form of LL-002 and changes no existing behaviour, so it adds no entry. The first change to its behaviour is the example pull request. Run `git show` on that commit to see the code and the entry together.
