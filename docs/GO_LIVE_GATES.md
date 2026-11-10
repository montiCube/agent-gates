# Go-live gates

Eight gates stand between a system built by agents and its first run on real input with real consequences. Gate 2 has a second half, Gate 2b, so there are nine rows. All nine must close.

Each gate is binary. It passes or it fails. There is no partial credit.

This file holds definitions only. It does not hold status. Status lives in one place, and that place is not here. In the source system this header once carried a per-gate snapshot. Within weeks it was wrong: it said day 10 of a soak that stood at day 28. The snapshot was deleted, and the header now points to the one file that holds status.

## Why this file exists

A list of known gaps names the holes. It does not say what closing them looks like. This file does. When every row passes, going live is defensible. Until then it is not.

The order is roughly by size of the unknown. Gate 1 is the largest. Gate 8 is the smallest. None is optional.

## Terms

- **Shadow mode.** The system runs the full pipeline and records every decision, but its actions have no real consequence.
- **Live mode.** Its actions have real consequences.
- **Automatic stop.** The system's own last-resort halt. It fires on a threshold, blocks new actions, and still lets the system wind down what it holds.
- **Halt flag.** A file. Setting it halts the system without killing the process.
- **The record.** The append-only log of every attempt the system makes: acted, rejected or skipped, each with its reason.

## Gate 1. Offline measurement

**Question.** Has the decision logic production will run been measured on recorded data, through production's own code path, against a bar written down before the run?

**Evidence.**
- A harness that runs the production code path end to end. Not a prototype. Not a copy of the logic.
- Costs included. A result that ignores what each action costs is not a result.
- A committed report per measured component, with the run configuration recorded: data range, inputs, parameters.
- The pass bar, stated before the run. The worst case seen offline must stay inside the automatic stop's threshold. If it does not, the stop will fire in production. That is a redesign, not a release.

**Checked by.** The harness writes the report. The human reads and merges it.

**Why.** In the source system the first harness measured a different piece of logic from the one production ran. Its numbers were real and irrelevant. A new harness was built on production's own code path, and this gate now requires one.

## Gate 2. Shadow soak

**Question.** Has the whole pipeline run end to end, unattended, in shadow mode, for 30 consecutive days?

**Evidence.**
- 30 consecutive calendar days on the real scheduler. No human intervention except clearing a halt the human set on purpose.
- The record holds at least one row of every outcome class the system can produce: acted, and each kind of skip.
- One deliberate halt during the window. Set the halt flag by hand. Confirm the next cycle takes no new action, and that the system can still wind down what it holds.
- A weekly snapshot of the record, archived. It is the baseline live behaviour is later compared against.

**Checked by.** A query over the record shows the outcome mix. The human reads the weekly snapshots.

**Why.** Offline measurement is necessary. It is not sufficient. In the source system, before this gate, the record file did not exist and the pipeline had never run end to end. The 30-day soak was its first full run, and it closed the gate.

## Gate 2b. Outcome soak

**Question.** In shadow mode, does the system produce the outcome it exists for, on a counted sample?

A soak that proves the system runs does not prove it works. In the source system Gate 2 closed first. Two days later its attestation was narrowed and this row was split out. A month after that, a ruling made it count toward go-live.

**Evidence.**
- The outcome measure and the unit of count, defined before day 0.
- Judged when n reaches 15 completed units, then at every further 15. If n has not reached 15 within 60 days of day 0, the gate is re-examined, not passed.
- Net outcome above zero, costs included.
- Costs no more than 25 percent of the gross outcome.
- No single unit carries more than half the net. If one does, the result is CONCENTRATED: a third state, not a pass and not a fail. It withholds release.
- A reset rule, not a date. A change that alters what the system does resets day 0. A restart that changes nothing does not.
- Every reset has a committed declaration file and a row in a segment table. A reset without the file is not a reset.
- Earlier segments stay as their own rows. They are never pooled.
- A failed attempt stays recorded as failed. The next attempt starts from a new day 0.

**Checked by.** A census script computes n and the net from the raw record. The result is reproduced on a second machine at the same as-of time. Inputs are cited by sha256.

**Why.** Without a reset rule, a soak can be restarted until it passes. Without the no-pooling rule, a good old segment can carry a bad new one.

## Gate 3. Alert path, fired for real

**Question.** When the system fails in production, does a human find out within minutes?

**Evidence.** All five, on the production host, not localhost:
- The alert endpoint returns a non-empty public key.
- At least one device is subscribed.
- A synthetic alert reaches the phone within 5 seconds.
- Setting the halt flag on the host produces a real alert within one scheduler tick, 5 minutes at most.
- Tapping the alert opens the system's own dashboard.

**Checked by.** The human, walking a runbook with the host open and the phone in hand. The five lines are the verification.

**Why.** Running unattended with no way to be alerted is the worst of both postures.

## Gate 4. Tests where the decisions are

**Question.** Is the code that decides what the system does covered by tests, and is that enforced?

**Evidence.**
- At least 80 percent line and branch coverage on each named module. Each module on its own, not an average.
- The module list lives in code, in the coverage script. Widening it is a code change, not a docs edit.
- A new decision module joins the list in the same commit as its coverage test.

**Checked by.** CI, on every push.

**Why.** In the source system the first 80 tests all exercised the health monitor. The modules that decided what to do, how much, and whether it fit had zero coverage. The suite tested the monitor, not the thing it monitored. This gate was written in response. It closed when each of the 8 modules it then named reached 80 percent. The list has since grown to 15.

## Gate 5. Continuous integration

**Question.** Can a change that breaks a gated module reach the main branch?

**Evidence.**
- A CI workflow runs the full check on every push and every pull request into main.
- The same workflow fails the build if any Gate 4 threshold regresses.
- Branch protection on main. No direct pushes. A pull request needs the CI check green and one approving review. In a solo setup, that review is the human's.

**Checked by.** Open a deliberately broken pull request. The check goes red. Merge is blocked.

The example in this repo adds one check: the build fails if the installed versions differ from the lock file.

## Gate 6. Auto-remediation, shadow first

**Question.** Has every automatic corrective action been shown correct in shadow before it was armed?

**Evidence.**
- Remediation ships shadow by default. It is armed by an environment setting, not by a code change.
- At least 7 calendar days of shadow log on the production host, with at least one entry of each failure class it handles.
- A human review of that log confirms every shadow action would have been the right response. The review notes are committed.
- After arming, within 7 days, at least one armed action fires correctly on a real event.

**Checked by.** The human, reading the log and the review. In the source system the gate closed on a controlled event with the human at the console: one induced failure, one automatic halt, one page, then ten 5-minute cycles refused over 47 minutes and a clean resume. The review of that event was committed with a ledger entry, and the gate closed.

**Why.** An automatic action that is wrong fires faster than a human can react. The shadow log is the proof that it would have been right.

## Gate 7. Process supervision

**Question.** If the main process dies, is it restarted, and does a human hear about it?

**Evidence.**
- A supervisor unit that restarts the process on failure, with logs kept.
- A liveness probe that checks two things: the unit is active, and the newest row in the record is younger than twice the probe interval. Either one failing is down. The probe has its own tests inside the Gate 4 suite.
- One staged crash. Kill the process with SIGKILL. The supervisor restarts it. The next probe records a brief degraded window, then recovery. An alert fires.

**Checked by.** The human runs the crash test. The journal and the alert log hold the trail.

**Why.** A process can be alive and doing nothing. Checking only that it is alive misses that.

## Gate 8. Written limits and a stop plan

**Question.** Are the limits of the first live run, and the points at which a human stops it, written and signed before it starts?

**Evidence.** One committed document naming:
- The initial scope of the live run.
- A staged scale-up plan. Each step is triggered by soak time and by live results, not by calendar time alone.
- Two manual stop lines: a soft line, review and consider stopping; and a hard line, stop now regardless of what the system says. Both are tighter than the automatic stop.
- An outage policy for a dependency down more than 1 hour, more than 24 hours, and more than 1 week. Decided in advance.
- A rollback policy: the conditions for returning to shadow mode.
- A sign-off line with the human's name and date.

**Checked by.** The human signs. If the document says so, the human's merge of it is the signature. It is reviewed quarterly.

**Rider.** If every protective action runs inside the process, a dead process protects nothing. Decide in writing where protection lives before going live, and record the ruling here.

**Why.** The automatic stop is the last line of defence, not the first. A threshold chosen at 3 a.m. during a real failure is the failure rule-based systems exist to prevent.

## Closing a gate

- A gate closes in a commit. That commit carries a ledger entry. See LOGIC_LEDGER.md.
- Evidence that rests on an open `[ASSUMPTION — verify]` marker does not close a gate. See ASSUMPTION_DISCIPLINE.md.
- If a gate closes with known gaps, the gaps are stated exactly, beside the closing note. If the human reads a gap as disqualifying, the flip is reverted before merge.
- Rulings on a gate arrive as comments on the pull request. Nothing automated rules on a gate.

## When a gate stops fitting

Systems change. In the source system the components Gate 1 named were retired by a redesign before the gate closed. The gate was not quietly edited. A dated note re-staked it against the new components, and the old text was kept below the note as history.

Do the same. A gate's history is part of its evidence.

## Going live

When all nine rows pass:

1. **Day 0.** The live credential enters the environment together with every setting that live mode needs, turned at once. The service should refuse to start with a live credential present unless all of them are set.
2. **Days 0 to 7.** The human is on alert and reviews the record daily.
3. **Days 8 to 30.** If no stop line is crossed and live results track the offline measurement within 50 percent either way, scope holds.
4. **Day 30 on.** The first scale-up step from Gate 8, at the human's discretion.

Crossing any Gate 8 line in the first 30 days returns the system to shadow mode. Full stop. Going live again needs a fresh review of the gate that failed and of any gate it touches.
