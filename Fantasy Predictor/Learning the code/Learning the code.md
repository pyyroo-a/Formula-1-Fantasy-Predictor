---
title: Learning the code
date: 2026-10-30
tags: [pitwall, learning, index]
aliases: [Learning the code, Code explained]
---

# Learning the code

I know how PitWall thinks (practice pace in, fantasy points out, best teams under
budget). These notes are about the other half: **the code that does it**, so the program
stops being a black box. Written in plain words with small real bits of our code, so I
can read them on my phone in my free time.

Read them in order, each one builds on the last:

1. [The big picture](1%20The%20big%20picture.md): the two halves of PitWall, how they talk, and where each one lives
2. [React in 10 minutes](2%20React%20in%2010%20minutes.md): the handful of ideas the whole website is built from
3. [The frontend, file by file](3%20The%20frontend%20file%20by%20file.md): what every folder and file in `frontend/src/` is for
4. [One page, from tap to screen](4%20One%20page%20from%20tap%20to%20screen.md): following the Garage all the way through
5. [The backend side](5%20The%20backend%20side.md): FastAPI, an endpoint, and the practice fix as a worked example
6. [Tests and checking](6%20Tests%20and%20checking.md): how we know a change didn't break anything

## The one sentence version

The **website** (React, on Vercel) is the shop window: it only shows things. The
**backend** (Python, on Render) is the kitchen: it does all the maths. The website asks
the kitchen questions over the internet ("what's this weekend's team?"), gets an answer
back as text called JSON, and draws it nicely.

## How to use these notes

- Open the file the note talks about next to it (in VS Code or on GitHub) and look for
  the bit it quotes. Seeing it in its real place helps a lot.
- Don't try to memorise anything. If a word is new, it's explained the first time it
  shows up, and there's a little word list at the bottom of each note.
- If a note and the code ever disagree, the code wins and the note needs fixing (same
  rule as the rest of the vault).

Related: [Start here](../README.md), [Frontend](../Frontend.md), [Code tour](../Code%20tour.md)
