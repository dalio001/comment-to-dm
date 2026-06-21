# Comment-to-DM Campaign Plan — 2026-06-18 reel batch (next week)

7 reels, 7 lead magnets. Each campaign is **prepped now, armed on publish day**.

## How it works (the timing rule)
A campaign needs the reel's **live Post ID**, which only exists *after* Meta publishes it.
You CANNOT arm a campaign before the reel is live. So:
1. Everything below is pre-written — copy/paste ready.
2. The morning each reel publishes: open the post → copy its Post ID → **Campaigns → New** →
   paste Post ID + the row below → toggle **Active**. ~30 seconds.

## Two-step DM (recommended, esp. Instagram)
The first DM asks them to reply one word. When they reply, the **follow-up** sends the link.
Replying moves the thread out of their Message Requests folder into the main inbox, and on
IG it satisfies Meta's "user messaged you first" rule. Fill `followup_message` with the link.

## Link host
PDFs are staged at `static/leads/`. Once the app is deployed, each link is:
`https://comment-to-dm.onrender.com/static/leads/<file>`  ← replace `YOUR_DOMAIN` after deploy.

---

## Day 1 — The cold kills first
- **Word:** `SHELF`
- **PDF:** `static/leads/day-1-the-cold-kills-first.pdf` (The Fridge Map)
- **Comment reply:** Sent you The Fridge Map 🐗 Check your DMs.
- **DM message:** You asked for The Fridge Map — every food and where it really belongs. Reply **YES** and I'll send it straight over.
- **Follow-up (link):** Here it is, friend — The Fridge Map: https://comment-to-dm.onrender.com/static/leads/day-1-the-cold-kills-first.pdf — The Sage.

## Day 2 — Honey never dies
- **Word:** `AMBER`
- **PDF:** `static/leads/day-2-honey-never-dies.pdf` (The Honey Guide)
- **Comment reply:** Sent you The Honey Guide 🐗 Check your DMs.
- **DM message:** You asked for The Honey Guide — how to tell real raw honey from the fake. Reply **YES** and I'll send it over.
- **Follow-up (link):** Here it is — The Honey Guide: https://comment-to-dm.onrender.com/static/leads/day-2-honey-never-dies.pdf — The Sage.

## Day 3 — Salt kept the winter
- **Word:** `CURE`
- **PDF:** `static/leads/day-3-salt-kept-winter.pdf` (The Salt Cure)
- **Comment reply:** Sent you The Salt Cure 🐗 Check your DMs.
- **DM message:** You asked for The Salt Cure — keeping food through any winter. Reply **YES** and it's yours.
- **Follow-up (link):** Here it is — The Salt Cure: https://comment-to-dm.onrender.com/static/leads/day-3-salt-kept-winter.pdf — The Sage.

## Day 4 — Bring the iron back
- **Word:** `IRON`
- **PDF:** `static/leads/day-4-bring-the-iron-back.pdf` (The Cast Iron Guide)
- **Comment reply:** Sent you The Cast Iron Guide 🐗 Check your DMs.
- **DM message:** You asked for The Cast Iron Guide — restore a rusted pan into a lifetime tool. Reply **YES** and I'll send it.
- **Follow-up (link):** Here it is — The Cast Iron Guide: https://comment-to-dm.onrender.com/static/leads/day-4-bring-the-iron-back.pdf — The Sage.

## Day 5 — The first ten minutes
- **Word:** `BLACKOUT`
- **PDF:** `static/leads/day-5-first-ten-minutes.pdf` (The Blackout Plan)
- **Comment reply:** Sent you The Blackout Plan 🐗 Check your DMs.
- **DM message:** You asked for The Blackout Plan — your calm first ten minutes in the dark. Reply **YES** and it's yours.
- **Follow-up (link):** Here it is — The Blackout Plan: https://comment-to-dm.onrender.com/static/leads/day-5-first-ten-minutes.pdf — The Sage.

## Day 6 — One box does it all
- **Word:** `SCRUB`
- **PDF:** `static/leads/day-6-one-box-does-it-all.pdf` (The One-Box Guide)
- **Comment reply:** Sent you The One-Box Guide 🐗 Check your DMs.
- **DM message:** You asked for The One-Box Guide — one cheap box of baking soda, the whole house. Reply **YES** and I'll send it.
- **Follow-up (link):** Here it is — The One-Box Guide: https://comment-to-dm.onrender.com/static/leads/day-6-one-box-does-it-all.pdf — The Sage.

## Day 7 — Seven you overpay for
- **Word:** `HANDS`
- **PDF:** `static/leads/day-7-seven-you-overpay-for.pdf` (The Seven)
- **Comment reply:** Sent you The Seven 🐗 Check your DMs.
- **DM message:** You asked for The Seven — seven things you overpay for, made at home for pennies. Reply **YES** and it's yours.
- **Follow-up (link):** Here it is — The Seven: https://comment-to-dm.onrender.com/static/leads/day-7-seven-you-overpay-for.pdf — The Sage.

---

## Still needed before any of this fires
1. **Deploy the app** to a public HTTPS domain (Railway/Render configs are in the repo) — without it
   there's no webhook for Meta to call and no working link. Then replace `YOUR_DOMAIN` above.
2. **Meta App Review** for the messaging permissions (or stay in Dev mode and test with your own accounts only).
3. **Per reel, on publish day:** paste the live Post ID into a new campaign + the row above, set Active.
