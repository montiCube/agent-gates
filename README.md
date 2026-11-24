# agent-gates

![CI](https://github.com/montiCube/agent-gates/actions/workflows/ci.yml/badge.svg)

## The problem

AI coding agents drift. They assert things they have not checked. They ship behavioural changes with no record of why. Over weeks this compounds into a system nobody fully understands.

## What this is

A governance layer for agent-driven development, in four parts:

- [Go-live gates](docs/GO_LIVE_GATES.md). Eight release gates in nine rows. Each passes or fails. No partial credit.
- [Logic ledger](docs/LOGIC_LEDGER.md). Shared memory across agents and across time. A behavioural change and its entry are one commit.
- [Assumption discipline](docs/ASSUMPTION_DISCIPLINE.md). Verify a load-bearing claim, or mark it `[ASSUMPTION — verify]` inline.
- [Adversarial board](docs/ADVERSARIAL_BOARD.md). Scheduled reviews whose only job is to find what is wrong. They consolidate the rulings the human must make, and never rule, merge or deploy.

Extracted from a private system that has run under these gates for several months.

## How to read it

Start with the go-live gates, then the logic ledger. Then open the example pull request, a merge commit in this repo's history:

```
git log --merges --format='%h %s'
git show <hash>^2
```

The second command shows the code change and its ledger entry, LL-003, in one commit. The example service and its CI are in `example/` and `.github/`.

## What CI enforces

`tools/check_governance.py` runs on every push and every pull request. It fails the build when:

- A commit changes a behaviour path and adds no ledger entry in that same commit, unless the commit ends with a `Ledger-Exempt: <reason>` trailer.
- A commit deletes, renames or rewrites an existing ledger entry. Adding one `Superseded by LL-NNN on YYYY-MM-DD.` line is the only change allowed.
- A commit adds an entry numbered at or below an entry that already exists.
- An entry lacks its title line or one of its five fields, or its title number differs from its file name.
- `ledger/DIGEST.md` differs from the digest generated from the entries.
- A changed file holds an open `[ASSUMPTION — verify]` marker, on a pull request or a push to `main`. On other pushes it is printed, not failed.

It judges only the commits in the change, not the history before it. See `ledger/LL-004.md`.

## Status and author

Status: first release. The CI steps pass when run locally on Python 3.12. CI has run on GitHub since the first push; the badge shows the current state. Author: Jake Raum. Brief: https://gist.github.com/montiCube/593face1bac109ed8ea01af63732da3c. Licence: MIT.
