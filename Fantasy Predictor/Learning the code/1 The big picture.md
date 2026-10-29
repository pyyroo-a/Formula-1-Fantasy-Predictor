---
title: 1 The big picture
date: 2026-10-30
tags: [pitwall, learning]
---

# 1. The big picture

## Two halves, like a restaurant

| | The website (frontend) | The backend |
|---|---|---|
| Restaurant version | the dining room and the menu | the kitchen |
| What it does | shows things, reacts to taps | the maths: predictions, teams, chips, ladders |
| Language | JavaScript, with React | Python, with FastAPI |
| Folder in the repo | `frontend/` | `src/`, `main.py`, `scripts/` |
| Where it runs | **Vercel** (free) | **Render** (free, falls asleep when nobody uses it) |
| Address | formula-1-fantasy-predictor.vercel.app | formula-1-fantasy-predictor.onrender.com |

The website never works anything out by itself. When it needs a number, it asks the
backend. That's why the site sometimes says "the free server can take up to 30 seconds
to wake up": Render puts the kitchen to sleep after a while, and the first order of the
day wakes it.

## How they talk: endpoints and JSON

The backend has a list of **endpoints**. An endpoint is just an address you can ask a
question at, like a counter in the kitchen with a name on it. They're all listed in
[API](../API.md). Two kinds:

- **GET** = "give me this", nothing to send. Like `GET /weekend-team`: "what's this
  weekend's team?"
- **POST** = "here's some info, work something out with it". Like `POST /transfer-ladder`:
  "here's my team, my budget and my free transfers, what should I do?"

The answer always comes back as **JSON**, which is just text written in a tidy shape the
computer can read. A real (shortened) answer from `/last-team`:

```json
{
  "race_name": "United States Grand Prix",
  "round": 18,
  "locked": true,
  "teams": [
    {
      "drivers": [{ "Abbreviation": "LEC", "Price": 24.1, "FantasyValue": 38.0 }],
      "total_score": 144.0,
      "boost_pick": { "Abbreviation": "LEC" }
    }
  ]
}
```

Curly brackets `{ }` are a box of named things (`"round": 18`), square brackets `[ ]`
are a list (the 3 teams). That's all JSON is.

## What happens when I open the site

1. My phone asks **Vercel** for the website. Vercel sends the files (the React code,
   the font link, the icons).
2. The website starts and asks **Render** a few questions at once: the races, the next
   race, prices, this weekend's team, the predicted finish.
3. Render's Python works out (or reads from a saved file) the answers and sends JSON back.
4. The website draws the main page from those answers.
5. When I tap something like the Garage, the website asks a new question
   (`/transfer-ladder`) and draws the answer.

## Where the saved stuff lives

Not everything is worked out live. Some things are slow, so they're done once and saved:

- **`data/snapshots/`**: each weekend's locked teams, saved after FP3 by the GitHub Action
  (see [Snapshots](../Snapshots.md)). That's why the answer never changes after the lock.
- **`data/track_record_2026.json`** and **`data/chip_history.json`**: worked out by
  scripts every Monday, the pages just read them.
- **My own stuff** (my Garage teams, my budget) is saved **in my browser only**, in
  something called `localStorage`. It's like a small notebook the browser keeps for each
  website. That's why my Garage teams on my phone aren't on my laptop.

## How new code gets to the live site

1. Claude (or me) changes files on my laptop.
2. I commit in GitHub Desktop and push to GitHub.
3. **Vercel** sees the push and rebuilds the website (about a minute).
4. **Render** sees the push and rebuilds the backend (a few minutes).

So a push is basically "press go" for both. That's also why there's the rule about no
backend pushes on a race weekend: a rebuild in the middle of the lock would be bad timing.

## Little word list

- **Frontend**: the part you see. **Backend**: the part that thinks.
- **Endpoint**: an address on the backend you can ask a question at.
- **JSON**: the text format the answers come back in.
- **Deploy**: putting new code live (Vercel and Render do it on every push).
- **localStorage**: the browser's small notebook for one website.

Next: [React in 10 minutes](2%20React%20in%2010%20minutes.md)
