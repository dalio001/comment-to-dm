# Comment-to-DM Automation (Instagram + Facebook)

A self-hosted, ManyChat-style tool. When someone comments a **keyword** on a post you're
tracking, it automatically **replies to the comment publicly** and **sends the commenter a
private DM** — on **both Instagram and Facebook**, from one dashboard.

Built only on the **official Meta Graph API**. No Selenium, no `instagrapi`, no unofficial APIs.

---

## Why one app for both

Instagram's Graph API and Facebook's Pages/Messenger API live on the same host
(`graph.facebook.com`), behind the same Meta Developer App. ~80% of this code is shared.
Each campaign just carries a `platform` flag.

| | Instagram | Facebook |
|---|---|---|
| Public reply | `POST /{comment-id}/replies` | `POST /{comment-id}/comments` |
| Private DM | `POST /{ig-account-id}/messages` (recipient = comment_id) | `POST /{comment-id}/private_replies` |
| Webhook field | `comments` (object: `instagram`) | `feed` (object: `page`) |
| Permissions | `instagram_manage_comments`, `instagram_manage_messages` | `pages_manage_engagement`, `pages_messaging`, `pages_read_engagement`, `pages_manage_metadata` |

> **Facebook is the more reliable half.** Its `private_replies` endpoint sends a Messenger DM
> *in direct response to a comment*, which sidesteps the 24-hour messaging window and the
> "user must DM you first" rule that limits the Instagram side (see [Limitations](#limitations)).

---

## Tech stack

- **Backend:** Python + FastAPI
- **DB:** SQLite via SQLAlchemy (swap `DATABASE_URL` for Postgres later — no code changes)
- **Frontend:** server-rendered Jinja2 + vanilla JS (no build step)
- **Deploy:** Dockerfile + `railway.toml` + `render.yaml`

---

## Project structure

```
/
├── main.py            # FastAPI app entry point + /health
├── graph.py           # Shared Graph API HTTP layer (logging + rate-limit backoff)
├── instagram.py       # Instagram Graph API client
├── facebook.py        # Facebook Pages/Messenger client
├── models.py          # SQLAlchemy models (Config, Campaign, ProcessedComment)
├── database.py        # DB session setup + env seeding
├── routes/
│   ├── webhook.py     # GET/POST /webhook/instagram and /webhook/facebook
│   ├── dashboard.py   # HTML dashboard routes
│   └── api.py         # REST API for campaigns + config + post preview
├── static/            # CSS + JS
├── templates/         # Jinja2 HTML
├── .env.example
├── Dockerfile
├── railway.toml
├── render.yaml
├── requirements.txt
└── README.md
```

---

## Run locally

```bash
cp .env.example .env          # then set WEBHOOK_VERIFY_TOKEN + FACEBOOK_APP_SECRET
pip install -r requirements.txt
python main.py                # or: uvicorn main:app --reload
```

Open **http://localhost:8000/dashboard**. Health check at **/health** → `{"status":"ok"}`.

To receive webhooks while developing locally, expose your port with a tunnel:

```bash
ngrok http 8000
# use the https URL Meta can reach, e.g. https://abc123.ngrok.io/webhook/instagram
```

---

## Meta setup — full step-by-step (you have no Developer App yet)

### 0. Prerequisites
- An **Instagram Business or Creator** account, and/or a **Facebook Page** you admin.
- For Instagram: the IG account must be **linked to a Facebook Page** (Page → Settings → Linked Accounts). This is how the Graph API reaches Instagram.

### 1. Convert your Instagram account
Instagram app → **Settings → Account type and tools → Switch to professional account** →
choose **Business** or **Creator**. Then link it to your Facebook Page.

### 2. Create a Facebook Developer App
1. Go to **https://developers.facebook.com** → **My Apps → Create App**.
2. Use case: **Other** → type **Business** → name it (e.g. "PLZ Comment Bot").
3. In the App Dashboard, note **App ID** and **App Secret** (Settings → Basic).
   Put the App Secret in `.env` as `FACEBOOK_APP_SECRET`.

### 3. Add products
In the App Dashboard → **Add product**:
- **Instagram Graph API** (for IG automation)
- **Messenger** and **Webhooks** (for FB automation)

### 4. Add permissions
Under **App Review → Permissions and Features**, request:
- Instagram: `instagram_manage_comments`, `instagram_manage_messages`, `instagram_basic`, `pages_show_list`
- Facebook: `pages_manage_engagement`, `pages_messaging`, `pages_read_engagement`, `pages_manage_metadata`

While in **Development mode** these work for users with a role on the app (you) without full
review. To run for the public you must submit these for **App Review** (see Limitations).

### 5. Generate a long-lived access token
Use the **Graph API Explorer** (App Dashboard → Tools → Graph API Explorer):
1. Select your app, click **Generate Access Token**, grant the permissions above.
2. This is a **short-lived** user token (~1 hour). Exchange it for a **long-lived** one (~60 days):
   ```bash
   curl "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
   ```
3. For Facebook actions you need a **Page access token**. Get it from the long-lived user token:
   ```bash
   curl "https://graph.facebook.com/v21.0/me/accounts?access_token=LONG_LIVED_USER_TOKEN"
   ```
   The `access_token` in that response (for your Page) is a **long-lived Page token** — use it as
   `FACEBOOK_PAGE_ACCESS_TOKEN`. Page tokens derived from a long-lived user token effectively
   don't expire as long as the user token is valid.

**Refreshing (tokens expire after ~60 days):** re-run the `fb_exchange_token` exchange before the
60-day mark to mint a fresh long-lived token, then re-fetch the Page token. Set a calendar reminder,
or automate it on a ~50-day cron. Paste the new token into the dashboard **Settings** page.

### 6. Get your account IDs
- **Instagram Business Account ID:**
  ```bash
  curl "https://graph.facebook.com/v21.0/me/accounts?fields=instagram_business_account&access_token=LONG_LIVED_USER_TOKEN"
  ```
- **Facebook Page ID:** shown in the same `me/accounts` response (`id` of the Page).

### 7. Configure webhooks
In App Dashboard → **Webhooks**:

**Instagram object:**
- Callback URL: `https://YOUR_DOMAIN/webhook/instagram`
- Verify token: the exact value of `WEBHOOK_VERIFY_TOKEN` from your `.env`
- Subscribe to the **`comments`** field.

**Page object:**
- Callback URL: `https://YOUR_DOMAIN/webhook/facebook`
- Verify token: same `WEBHOOK_VERIFY_TOKEN`
- Subscribe to the **`feed`** field.
- Also subscribe your **Page** to the app's webhooks:
  ```bash
  curl -X POST "https://graph.facebook.com/v21.0/PAGE_ID/subscribed_apps?subscribed_fields=feed&access_token=PAGE_ACCESS_TOKEN"
  ```

When you click "Verify and Save", Meta calls `GET /webhook/...` with a challenge — this app answers
it automatically as long as the verify token matches.

### 8. How to get a Post ID
- **Instagram media ID:**
  ```bash
  curl "https://graph.facebook.com/v21.0/IG_BUSINESS_ACCOUNT_ID/media?access_token=TOKEN"
  ```
  Each item's `id` is the media/Post ID. (Graph API Explorer: query `me` → `media`.)
- **Facebook post ID:**
  ```bash
  curl "https://graph.facebook.com/v21.0/PAGE_ID/posts?access_token=PAGE_TOKEN"
  ```
  Use the returned `id` (format `PAGEID_POSTID`).

### 9. Enter credentials + create a campaign
1. App → **Settings**: paste IG token, IG Business Account ID, FB Page ID, FB Page token. Save.
2. App → **Campaigns → New campaign**: pick platform, paste a Post ID (a preview loads on blur),
   set comma-separated keywords, the public reply text, and the DM text. Save and toggle **Active**.

Now comment a keyword on that post from a second account — you should get a public reply + a DM.

---

## How matching works
- Keywords are **case-insensitive, partial** matches (`"link"` matches `"send me the LINK pls"`).
- Multiple keywords are OR'd; any match fires the campaign.
- Each comment ID is recorded in `ProcessedComment` so it **never fires twice**, even if Meta
  re-delivers the event. (Marked processed only after a successful send, so transient API failures
  retry on Meta's next delivery.)
- The app ignores comments authored by your own IG account / Page to avoid reply loops.

---

## Security
- `FACEBOOK_APP_SECRET` validates the **`X-Hub-Signature-256`** header on every webhook POST.
  Requests with a missing/incorrect signature are rejected with 403. (If the secret is unset, the
  app logs a warning and skips validation — **dev only**.)
- `WEBHOOK_VERIFY_TOKEN` guards the GET verification handshake.
- Credentials live server-side (DB / env). The dashboard only ever shows a **masked** token and
  never sends the raw secret back to the browser.
- `.env` and `*.db` are git-ignored.

---

## Limitations
**Messaging-window / permissions reality (read this):**
- **Instagram:** sending a DM via the Graph API generally requires either that the user messaged
  your business first, **or** the app holds **`instagram_manage_messages`** with an approved use
  case. Comment-triggered **private replies** are allowed within Meta's window but still require the
  approved permission for production (non-test) users. Apply via **App Review**, describing the
  comment-to-DM use case and providing a screencast.
- **Facebook:** `private_replies` is allowed **once per top-level comment** and must be sent within
  Meta's allowed window after the comment. It requires `pages_messaging`. This is the more permissive
  path and is what most ManyChat-style FB flows use.
- In **Development mode**, everything works for users who have a **role on your app** (you + testers)
  without full review — perfect for testing before you submit for App Review.

**Rate limits:** all Graph calls retry with exponential backoff on 429 / Meta rate-limit codes
(`graph.py`). High comment volume should still respect Meta's per-app limits.

---

## Deploy

**Railway:** push the repo, Railway reads `railway.toml`, builds the Dockerfile, health-checks
`/health`. Set `WEBHOOK_VERIFY_TOKEN` and `FACEBOOK_APP_SECRET` in the Railway dashboard. For
persistence across redeploys, attach a Postgres plugin and set `DATABASE_URL` (SQLite on Railway is
ephemeral).

**Render:** `render.yaml` defines a Docker web service with the `/health` check. Set the secret env
vars in the Render dashboard.

**Docker (anywhere):**
```bash
docker build -t comment-to-dm .
docker run -p 8000:8000 --env-file .env comment-to-dm
```

---

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | `{"status":"ok"}` health check |
| GET/POST | `/webhook/instagram` | IG verification + comment events |
| GET/POST | `/webhook/facebook` | FB verification + comment events |
| GET | `/dashboard`, `/settings` | Web UI |
| GET/POST | `/api/config` | Read (masked) / save credentials |
| GET/POST/PUT/DELETE | `/api/campaigns` | Manage campaigns |
| POST | `/api/campaigns/{id}/toggle` | Activate / pause |
| GET | `/api/post-preview` | Fetch post thumbnail + caption |
