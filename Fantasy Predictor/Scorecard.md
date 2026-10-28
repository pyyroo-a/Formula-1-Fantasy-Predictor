---
title: Scorecard
date: 2026-10-28
tags: [pitwall, scorecard]
---

# Scorecard

Made on 2026-10-28 with `python scripts/scorecard.py --rules current`, so the replay uses the `current` forecast rules. Every team is graded the same way and all points are official F1 Fantasy points, straight from the game's own feed (`data/official_points_2026.json`), not our version of the rules.

- **Locked**: team 1 of what PitWall really locked that weekend.
- **PitWall replay**: the same build replayed walk forward, only using what was known before that race (FP3, or sprint quali on sprint weekends).
- **FP3 order**: the fastest cars in that session that fit, no model.
- **Most expensive**: spend as much of the $100M as possible.
- **Crowd**: the most owned team that fits, from the ownership saved at the lock.
- **Hindsight best**: the best team you could have had, the ceiling.

Everything is at $100M, each race a fresh team (no transfer limits), and everyone gets a 2x pick. A "-" means we don't have it, the reasons are under the table.

| Race | Locked | PitWall replay | FP3 order | Most expensive | Crowd | Hindsight best |
|---|---:|---:|---:|---:|---:|---:|
| R1 Australian Grand Prix | - | - | 220.0 | 132.0 | - | 290.0 |
| R2 Chinese Grand Prix | - | - | 329.0 | 206.0 | - | 461.0 |
| R3 Japanese Grand Prix | - | 248.0 | 248.0 | 130.0 | - | 273.0 |
| R4 Miami Grand Prix | - | 232.0 | 171.0 | 265.0 | - | 332.0 |
| R5 Canadian Grand Prix | - | 102.0 | 104.0 | 214.0 | - | 305.0 |
| R6 Monaco Grand Prix | - | 178.0 | 178.0 | 154.0 | - | 297.0 |
| R7 Barcelona Grand Prix | - | 127.0 | 115.0 | 71.0 | - | 262.0 |
| R8 Austrian Grand Prix | - | 226.0 | 226.0 | 138.0 | - | 243.0 |
| R9 British Grand Prix | - | 294.0 | 231.0 | 207.0 | - | 345.0 |
| R10 Belgian Grand Prix | - | 223.0 | 223.0 | 187.0 | - | 257.0 |
| R11 Hungarian Grand Prix | - | 229.0 | 212.0 | 211.0 | - | 257.0 |
| R12 Dutch Grand Prix | - | 198.0 | 220.0 | 125.0 | - | 295.0 |
| R13 Italian Grand Prix | 147.0 | 256.0 | 205.0 | 314.0 | - | 428.0 |
| R14 Spanish Grand Prix | 145.0 | 145.0 | 129.0 | 155.0 | - | 199.0 |
| R15 Azerbaijan Grand Prix | 99.0 | 178.0 | 88.0 | 21.0 | - | 270.0 |
| R16 Bahrain Grand Prix | 212.0 | 159.0 | 231.0 | 215.0 | - | 339.0 |
| R17 Singapore Grand Prix | 265.0 | 265.0 | 227.0 | 128.0 | - | 298.0 |
| R18 United States Grand Prix | 183.0 | 203.0 | 242.0 | 159.0 | - | 276.0 |
| **Average per race (races)** | 175.2 (6) | 203.9 (16) | 199.9 (18) | 168.4 (18) | - | 301.5 (18) |
| **Average on the replay's races** | 175.2 (6) | 203.9 (16) | 190.6 (16) | 168.4 (16) | - | 292.2 (16) |
| **Races the replay beat it** |  |  | 8 of 16 | 11 of 16 | - | 0 of 16 |

With these rules the replay rebuilt the exact locked team on 2 of 6 locked weekends, not on R13, R15, R16, R18.

Why some cells are "-":

- **Locked**, R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12: not locked, the weekend lock started at round 13.
- **PitWall replay**, R1, R2: the model needs 2 races of 2026 form first.
- **Crowd**, R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R16, R17, R18: no ownership saved at the lock, we only started saving it after the US GP.

Related: [Decisions and evidence](Decisions%20and%20evidence.md), [Fantasy scoring](Fantasy%20scoring.md), [Start here](README.md)
