# Assumption discipline

## The rule

An agent verifies every load-bearing claim against ground truth, or marks it inline:

```
[ASSUMPTION — verify]
```

There is no third option.

A claim is load-bearing if something else rests on it: a decision, a gate, a status, a number another document copies.

## Ground truth

In order of authority:

1. Running code and the live API.
2. The data store the system writes.
3. Committed documents.
4. Remarks, in chat or in comments.

Higher beats lower. A document that disagrees with the code is wrong until shown otherwise. A plan is a plan, not a record.

## Verifying

Verifying means naming what was run or read, and what it returned. "I checked" is not verification. The command and its output are.

## The marker

- Exact text, inline, at the point of the claim. Not in a footnote. Not in a summary at the end.
- Searchable: `grep -rn "ASSUMPTION — verify"`. Inside backticks, as here, it is a mention, not a marker.
- A marker is not a failure. It is an honest claim with its status attached.
- It is resolved one of two ways. Verify the claim and replace the marker with the source. Or delete the claim.
- Evidence that rests on an open marker does not close a gate. The pull request template asks about open markers in every change.

## Worked example

This happened in the source system. The marker was not used. The steps below show what it would have changed.

**The claim.** An analysis stated that a per-item calibration table had never gone live, so the offline model was still using a flat fallback value. A conclusion was built on it: the model was overcharging by about 2.5 times.

**Where it came from.** An evidence document still had a checkbox reading "pending". The analysis trusted the document over the store.

**With the marker.** The sentence would have read:

> The calibration table never went live. [ASSUMPTION — verify]

The conclusion built on it would have inherited the marker. Nobody could have treated it as settled.

**The verification.** One query against the store. The table held 27 rows, written 25 days earlier. 25 of the 27 items had 10 or more samples, enough to be active. The other 2 correctly used the fallback.

**The resolution.** The claim was retracted the same day the query was run. A ledger entry recorded the error and how it was made: a document trusted over the store. The stale checkbox was ticked with its real date. The conclusion that had leaned on the claim was withdrawn.

## A code-level case

The same failure happens in code. A function's docstring says what it returns. A test patches the function out, so the test passes whatever the function does. The docstring is now an unverified claim with a green check beside it. See `ledger/LL-003.md` and the example pull request.

## Why it matters

Unflagged assumptions are how agents lie by accident.

An agent writes a plausible sentence it has not checked. The sentence reads exactly like one it has checked. The next agent has no memory of how it was written. It reads the sentence as fact and builds on it. After a few rounds nobody can tell which parts were ever true.

The marker puts the difference on the page, at the point of the claim, where the next reader will see it.
