---
title: Prices
date: 2026-10-25
tags: [pitwall, prices, data]
---

# Prices

Where driver and constructor prices come from. Code in `src/fetch_prices.py`.

## The feed

The official F1 Fantasy site publishes a public JSON feed per round
(`fantasy.formula1.com/feeds/drivers/<round>_en.json`). `fetch_prices(round)` reads it
and `parse_price_feed` turns it into `{"drivers": {"VER": 28.2, ...}, "constructors": {...}}`.

Prices get fetched in two places:
- **Backend startup** (`main.py`): prices for the UPCOMING round (latest finished round
  + 1), since that's what the game charges for this weekend's team. Falls back to the
  finished round if the next one isn't published yet. Also works out the change vs
  the round before for the prices panel (`/price-changes`).
- **The Monday job** (`scripts/update_data.py`): refreshes `data/prices.json` and adds
  the round to `data/price_history.json`.

When a weekend gets locked, the snapshot build fetches that round's prices fresh, and
falls back to whatever the server loaded at startup.

## The duplicate driver trap

After a driver moves team mid season, the feed keeps his OLD driver and team pairing
as a second row with the same 3 letter code, marked `IsActive` 0 and frozen at the
old price. A plain dict let whichever row came last win, so Lawson got stored at 15.1
(his Red Bull price) instead of about 9.3 for rounds 15 to 17. I spotted it because
his price looked wrong in the app.

`parse_price_feed` now prefers the active row whatever the order. Don't "fix" it by
throwing inactive rows away instead: `IsActive` means "this pairing is current", not
"active this round", so in an old round's feed a driver who has since moved has no
active row at all (Hadjar in round 12), and strict filtering punches holes in the
price history. Side effect, on purpose: a driver who's off the grid keeps his last
price (Tsunoda 9.7 from round 15), which doesn't matter because he has no practice
laps so he never ends up in a team.

## Budget

The game grows your team value as your drivers get more expensive, so most people
play with more than $100M (I was around $107.5M). The Manual Team page remembers
your own budget in the browser (`pitwall_budget` in localStorage). The 3 locked teams
are still built at exactly $100M, because they're shared by everyone.

## Known gaps

- Round 14 is missing from `price_history.json` completely, all 23 drivers and 11
  constructors. A gap in the data job, not the parser. On the [Roadmap](Roadmap.md).

Related: [Gotchas](Gotchas.md), [Race weekend flow](Race%20weekend%20flow.md), [Fantasy scoring](Fantasy%20scoring.md)
