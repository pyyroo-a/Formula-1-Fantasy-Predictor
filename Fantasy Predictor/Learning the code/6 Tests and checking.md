---
title: 6 Tests and checking
date: 2026-10-30
tags: [pitwall, learning, testing]
---

# 6. Tests and checking

A test is a tiny program that checks one thing in my real code, by itself, every time.
Like a pre-race checklist: tyres on, fuel in, radio working. It takes seconds, it never
forgets a step, and it shouts if something's wrong.

PitWall has two sets:

| | Backend tests | Frontend tests |
|---|---|---|
| Where | `tests/` | `frontend/src/lib/*.test.js` |
| Tool | pytest (Python) | Node's own test runner |
| How to run | `./venv/Scripts/python.exe -m pytest -q` | `npm test` in `frontend/` |
| How many (2026-10-30) | 216 | 44 |

## What a frontend test looks like

From `lib/garage.test.js`, using the real numbers the live server gave for an example
team at the US GP:

```js
const ROWS = [{ transfers: 0, paid: 0, expected: 128.2 }, { transfers: 1, paid: 0, expected: 155.0 },
              { transfers: 2, paid: 0, expected: 188.5 }, { transfers: 3, paid: 0, expected: 205.1 }];

test("ladderSteps rounds like the planner always did", () => {
  const s = ladderSteps(ROWS);
  assert.deepEqual(s.map(x => x.expected), [128, 155, 189, 205]);
  assert.deepEqual(s.map(x => x.vsKeep), [null, 27, 61, 77]);
  assert.deepEqual(s.map(x => x.best), [false, false, false, true]);
});
```

Read it as: "give the rulebook these 4 rows, and check it says 128, 155, 189, 205, with
+27, +61, +77 and the last one as the best". `assert` means "this must be true, or stop
and complain". If I ever change the rounding by accident, this goes red straight away.

## What a backend test looks like

From `tests/test_openf1.py`, the one for the reviewer's fix:

```python
def test_an_empty_answer_is_not_remembered(fake_openf1, monkeypatch):
    answers = iter([[], LAPS])     # first OpenF1 says "no laps", then it has them
    ...
    with pytest.raises(of1.NotPublishedYet):
        of1.openf1_grid(2026, "United States Grand Prix", "FP2", START, now=later)
    grid = of1.openf1_grid(2026, "United States Grand Prix", "FP2", START, now=later)
    assert grid["Abbreviation"].iloc[0] == "LEC"
```

"Pretend OpenF1 is empty the first time and has laps the second time. The first ask must
say not published, the second must work and put Leclerc on top." The `fake_openf1` bit
means the test never touches the real internet: it swaps OpenF1 for canned answers, like
practising pit stops with a dummy car.

## The golden tests

Some backend tests are special. `tests/golden/` holds saved answers from every endpoint.
The test asks each endpoint again and checks the answer is **exactly** the same as the
saved one. So if I move code around and a number changes by even 0.1, a test fails. It's
what lets us tidy the backend without being scared of changing a prediction by accident.
See [How-tos](../How-tos.md) for re-recording them on purpose.

## Test first

The way we built the redesign: **write the test, watch it fail, then write the code,
watch it pass.** Watching it fail first matters. A test that passes before the code even
exists isn't testing anything. It's like checking the warning light works by unplugging
the sensor first: if the light doesn't come on, the light is broken, not the car.

## The other checks

- `npm run build`: builds the real website. If this fails, Vercel would fail too.
- `npm run lint`: a spell checker for code style. 4 old errors are known and allowed,
  new ones aren't.
- `tests/test_no_dashes.py`: fails if an em or en dash sneaks into anything I wrote. My rule.
- **The walk**: open every page at laptop and phone width (375px) and look. Tests check
  rules, the walk checks it actually looks right.

## What tests don't cover

The pages themselves (the drawing) have no automatic tests, only the rules in `lib/` do.
That's on purpose: drawing changes a lot and is quick to check by eye, rules don't change
much and are easy to get wrong silently. So: rules get tests, pages get the walk.

## Little word list

- **Test**: a tiny program that checks one thing.
- **Assert**: "this must be true".
- **Fake / mock**: a pretend version of something outside (like OpenF1), so tests don't
  need the internet.
- **Golden file**: a saved correct answer to compare against.
- **Red / green**: failing / passing.

Back to the start: [Learning the code](Learning%20the%20code.md)
