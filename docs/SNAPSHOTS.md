# Weekend snapshots

## Why we have these

The site used to work the fantasy team out again every time someone opened it. So
the answer depended on what time it was, whether Render had just restarted, and
whether FastF1 downloaded properly on that request. At Madring that meant the team
changed during the race and the predicted finishes vanished.

Now each race weekend gets worked out **once**, after final practice, and saved as a
file in `data/snapshots/`. The site only reads those files. They get committed to
GitHub, so restarts and redeploys can't lose them.

Each file holds the 3 teams (with chips and DNF numbers) and the predicted finishing
order. Old ones are kept, so predicted vs actual works for every race.

## How a race weekend goes

1. **Before final practice:** the site shows a live preview marked **PROVISIONAL**.
   It can still change.
2. **Final practice finishes and F1 publishes it** (FP3, or FP1 on sprint weekends).
3. **Within about 10 minutes** cron-job.org calls `POST /snapshot/auto` on Render.
   Render builds the snapshot, saves it and commits it to GitHub.
4. GitHub gets a commit like `chore: snapshot for Spanish Grand Prix (round 14)` and
   Render redeploys with it. The site now shows **LOCKED** and won't change.
5. **After the race** the snapshot stays up as the **HELD** team until the next race
   gets its own snapshot. Once results are published, the actual finishes show up
   next to the predictions.

We check F1's timing server before building, so "not published yet" (normal, just
wait) and "published but broken" (a real problem) never get mixed up. That mix up
is what hid the failed locks at Madring.

## One-time setup

You need three things. All free.

### 1. A secret for the endpoint

This stops random people from triggering builds. Make a random string:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

On Render, open the backend service, go to **Environment**, and add
`SNAPSHOT_SECRET` with that value. Keep a copy, cron-job.org needs it too.

### 2. A GitHub token so Render can commit the snapshot

1. On GitHub: profile picture > **Settings** > **Developer settings** >
   **Personal access tokens** > **Fine-grained tokens** > **Generate new token**.
2. **Repository access:** Only select repositories > `Formula-1-Fantasy-Predictor`.
3. **Permissions:** Repository permissions > **Contents** > **Read and write**.
   Nothing else.
4. Pick an expiry and put a reminder in your calendar a few days before it.
5. On Render, add it as `GITHUB_TOKEN`.

Adding env vars on Render redeploys the backend, give it a couple of minutes.

### 3. Check it works with a dry run

A dry run builds everything and shows you the result, but saves and commits nothing:

```bash
curl -X POST "https://formula-1-fantasy-predictor.onrender.com/snapshot/auto?dry_run=true" -H "X-Snapshot-Secret: YOUR_SECRET"
```

What you should get back:
- `"status": "idle"` when there's no race weekend on. That's fine, it means the
  secret works.
- `"status": "waiting"` during a weekend before final practice is out.
- `"status": "dry_run"` with the teams once final practice is published.
- `401` means the secret doesn't match. `503` means `SNAPSHOT_SECRET` isn't set.

(The first call after Render has been asleep can take about a minute.)

### 4. The scheduler on cron-job.org

1. Make a free account on [cron-job.org](https://cron-job.org) and create a new cronjob.
2. **URL:** `https://formula-1-fantasy-predictor.onrender.com/snapshot/auto`
3. **Schedule:** every 10 minutes, only on **Friday and Saturday**. Fridays are
   there for sprint weekends, which lock on FP1.
4. In the advanced settings, set the **request method to POST** and add a header
   `X-Snapshot-Secret` with your secret.
5. Save it.

The very first call each Friday might show as a timeout in cron-job.org because
Render is waking up. That's fine. Pings every 10 minutes keep Render awake for the
rest of the weekend, and the build itself runs in the background, so it never waits
on cron-job.org.

## If it didn't lock

Check `/weekend-team` on the backend. If it says `"locked": true` you're fine.

If not, call the dry run above to see why. Every reply includes `last_result`, which
shows the last build attempt and its error if it failed.

### Backup: lock it from your laptop

```bash
python scripts/lock_team.py
git add data/snapshots
git commit -m "snapshot for <race>"
git push
```

It builds exactly the same snapshot the automatic one would. It refuses to build if
the race results are already in the data, because then the model would have seen the
answers.
