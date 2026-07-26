# Future Plans & Roadmap

> Living doc. The north star: **build a career in the F1 industry.** Everything here
> is chosen to move toward that, not just to build cool things. Edit freely, since this is
> meant to grow. A dedicated planning chat will use this file as its starting context.

---

## The framing (read this first)

I probably won't get "noticed by an F1 team" directly, because that's rare and mostly luck.
What I *can* engineer is getting noticed by the **F1 data community and the people who
hire into it**: FastF1's maintainers, the F1 data folks on X/Reddit, engineers at teams
and their tech partners (AWS, timing/strategy suppliers, analytics companies).

That community is **small, public, and reachable**. Reputation there is what actually
converts to a job. So every project and contribution should point at *that* audience.

**Consistency beats one flashy drop.** A steady public track record (documented, posted)
is what hiring managers read. The honest-engineering angle, for example PitWall's backtest
where the dumb baseline beat my model, is a *feature*, not a weakness, to talk about.

---

## The three threads (one arc, not three separate things)

### 1. Contribute to FastF1: highest signal, lowest competition. **Start here.**
FastF1 is used by almost everyone doing public F1 data work. A merged PR is a credential
the community actually recognizes, worth more than another personal repo.

- Begin with **docs fixes plus "good first issue"** tickets, not a big feature (high acceptance, teaches the codebase).
- Best first PRs come from **papercuts I've already hit** using FastF1 in PitWall
  (for example the `enable_cache` crash when the cache dir doesn't exist, exactly this kind of thing).
- Deepens the real skill teams care about: working with live timing/telemetry data.
- **Next action:** browse open issues and docs gaps, list rough edges I've personally hit, scope ONE small mergeable PR.

### 2. New flagship project: a **race strategy simulator**. The "F1-job-shaped" build.
Fantasy (PitWall) is fun but not what teams do. Race strategy *is* a real engineering role,
underserved in public tools, and great for viral viz (F1 X loves strategy/telemetry graphics).

Possible scope (start small, grow):
- Tire degradation model (per compound, per circuit) from FastF1 stint data
- Pit-window and undercut/overcut calculator
- Safety-car / VSC "what-if" scenarios
- Optimal strategy given starting position plus tire allocation

Built on FastF1 data, so it reinforces thread 1. This is the one most likely to
**demonstrate a hireable skill AND get noticed.**

Alternative project ideas (parking lot):
- Driver-vs-driver telemetry corner analysis tool
- Qualifying gap / track-evolution analyzer
- Live race dashboard

### 3. Document and post: the amplifier (not an afterthought)
- Short write-up per milestone: what I built, the honest evaluation, what failed.
- Post to LinkedIn on a regular cadence, since the track record is the point.
- Reuse the honesty framing: shipping the baseline over the flashy-but-worse model.

---

## PitWall's role going forward
Stays my **polished, deployed showpiece**, the thing that looks finished. This is where
the UI redesign fits: make it look done, keep it low-maintenance, use it as proof I can
ship and maintain a real full-stack ML app. Not the flagship, but the credibility anchor.

---

## Recommended sequence
1. **FastF1**: one small PR (fast credible win plus community entry).
2. **Strategy simulator**: the flagship, built incrementally.
3. **Document both loudly**: steady LinkedIn cadence throughout.
4. **PitWall**: finish the UI, keep it as the polished anchor.

---

## For the dedicated future-plans chat
When I open that chat, start by:
- Dropping in this file for context.
- Picking ONE thread to make concrete (my instinct: FastF1 first).
- Turning it into actual next actions (specific issue to tackle / first module to build).

## Career reference (fill in over time)
- Target roles: data engineer, ML engineer, race strategist, simulation engineer, performance analyst, software engineer.
- Where they live: F1 teams plus tech partners (AWS, timing/strategy suppliers, sports-analytics firms).
- Community to plug into: FastF1 GitHub and Discord, F1 data X/Twitter, r/F1Technical, r/formula1.
