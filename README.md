# agent-gates

## The problem

AI coding agents drift. They assert things they have not checked. They ship behavioural changes with no record of why. Over weeks this compounds into a system nobody fully understands.

## What this is

A minimal governance layer for agent-driven development, in four parts:

- [Go-live gates](docs/GO_LIVE_GATES.md). Eight release gates in nine rows. Each passes or fails. No partial credit.
- [Logic ledger](docs/LOGIC_LEDGER.md). Shared memory across agents and across time. A behavioural change and its entry are one commit.
- [Assumption discipline](docs/ASSUMPTION_DISCIPLINE.md). Verify a load-bearing claim, or mark it `[ASSUMPTION — verify]` inline.
- [Adversarial board](docs/ADVERSARIAL_BOARD.md). Scheduled reviews whose only job is to find what is wrong. They hold at rulings and never merge or deploy.

Extracted from a private system that has run under these gates for several months.

## How to read it

Start with the go-live gates, then the logic ledger. Then open the example pull request, a merge commit in this repo's history:

```
git log --merges --format='%h %s'
git show <hash>^2
```

The second command shows the code change and its ledger entry, LL-003, in one commit. The example service and its CI are in `example/` and `.github/`.

## Status and author

Status: first release. The CI steps pass when run locally on Python 3.12. CI runs on GitHub from the first push. Author: Jake Raum. Brief: https://gist.github.com/montiCube/593face1bac109ed8ea01af63732da3c. Licence: MIT.
