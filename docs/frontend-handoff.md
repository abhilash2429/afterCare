# AfterCare frontend handoff

The working brief for the frontend owner and any frontend coding agent. Updated 2026-09-18 evening.
Freeze: **Sun 2026-09-20 14:00 IST**.

## 1. Where the codebase is

The backend is complete, deployed to `ap-south-1`, and tested live. There is no frontend in the repo yet.

- Backend: one Python 3.12 Lambda behind a Lambda Function URL (`api/`), plus a reminder Lambda.
- Test suite: 402 passing (`.venv\Scripts\python -m pytest -q`).
- Contract: `docs/api/openapi.yaml`. **This file is the source of truth for every request and response shape.** If this doc and the OpenAPI file disagree, the OpenAPI file wins; tell the backend owner.
- Product and safety rules: `docs/spec.md`.

Live checks already passed:
- caregiver invite and join (single use)
- get plan
- adherence
- mark given
- audio
- presigned upload
- reminder with a follow-up check schedule
- cross-circle 403
- caregiver blocked from owner actions

Owner-only flows (extract, patch, activate) need a real Cognito login, so the frontend is their first live test.

### Live values

```text
NEXT_PUBLIC_API_BASE          = https://ctj5ower7vmwubklgwntkqdwsi0aemrx.lambda-url.ap-south-1.on.aws
NEXT_PUBLIC_COGNITO_POOL_ID   = ap-south-1_UQXeokR8X
NEXT_PUBLIC_COGNITO_CLIENT_ID = 5u4d70pcibfkqq77d3qmccjneh
NEXT_PUBLIC_VAPID_PUBLIC_KEY  = BKqD2yl293BFI56RCMGAsL51qTtILmZ9-66CE41-_Rr6E7DxktmQCJ_R0qDNNWfUIDqbZrQ7V-UpnCKhPfmLYgU
Region                        = ap-south-1
```

- CORS on the API allows every origin, so localhost and Amplify both work.
- No trailing slash on the API base.

### Demo data (already seeded live)

- **Circle:** `ci_demo` ("Kulkarni family", language `kn`).
- **Active plan:** `pl_demo`, 5 medicines:
  - Ecosprin 75, morning, after food
  - Clopitab 75, night, after food
  - Atorva 40, bedtime
  - Pan 40, morning and night, before food, 14 days
  - Glycomet GP1 500, morning and night, after food
- **Dose history:** 3 days, mostly given, with one missed night dose. Today's doses are pending.
- **Redflags:** from the document.
- **Re-seeding:** the backend owner runs `python -m scripts.seed_demo --web-origin <your site>`. It resets the demo and prints a fresh one-time caregiver invite link. Ask for one whenever you need to log in as a caregiver.

## 2. Frontend stack and hard constraints

- Next.js 15, TypeScript, App Router, Tailwind, `output: "export"`, `images: { unoptimized: true }`. Hosted on Amplify Hosting as static files.
- `web/` already holds `AGENTS.md` (instructions for frontend coding agents). `create-next-app` needs an empty folder, so move it out first:
  `Move-Item web/AGENTS.md web/AGENTS.md.handoff; npx create-next-app@15 web --typescript --tailwind --app --no-src-dir --use-npm; Move-Item web/AGENTS.md.handoff web/AGENTS.md`
- Client-side fetching only. No SSR, server actions, API routes or edge runtime.
- All API calls go through one typed client, for example `web/lib/api/client.ts`. Components never build URLs or parse errors themselves.
- Read the API base from `NEXT_PUBLIC_API_BASE`. Never hardcode it.
- Develop against the mock when the live API is inconvenient:
  ```powershell
  npx @stoplight/prism-cli mock docs/api/openapi.yaml -p 4010
  ```
- Work on a branch `frontend/<name>`, and touch only `web/` unless agreed. Never edit `api/`, `infra/` or `openapi.yaml` to make the UI work. Ask the backend owner instead.

## 3. Auth model

There are two kinds of user. Both send `Authorization: Bearer <token>`.

| Who | Token | How they get it | Can do |
|---|---|---|---|
| Owner (family member who set it up) | Cognito **ID token** | Email one-time code (passwordless) | everything |
| Caregiver (whoever gives the medicines) | AfterCare session token (90 days) | Opens an invite link, `POST /circles/{circleId}/join` | view schedule, mark given, Box Check, upload strip photos, audio, adherence |

### Owner sign-in

The Cognito pool uses email as the username. Self sign-up is on, and the first sign-in factor can be `EMAIL_OTP`. With Amplify Auth v6 (`aws-amplify`), the flow is:

1. `signUp({ username: email, options: { userAttributes: { email } } })` for a new user, then `confirmSignUp`.
2. `signIn({ username: email, options: { authFlowType: "USER_AUTH", preferredChallenge: "EMAIL_OTP" } })`.
3. `confirmSignIn({ challengeResponse: code })` with the code from the email.
4. `fetchAuthSession()` and use `tokens.idToken.toString()` as the bearer. **Use the ID token, not the access token.**

Verify these calls against the current Amplify v6 passwordless docs; I have not run them from a browser. Emails come from `abhilashreddymand@gmail.com` through SES. SES is still in sandbox, so login emails only reach verified addresses. Tell the backend owner which test emails to verify.

### Owner tokens and circleId

An owner token carries no circleId, so **every owner call must pass `circleId`**: in the JSON body for POST and PATCH, or `?circleId=` for GET. A caregiver token carries its own circleId, so caregivers may omit it.

### Caregiver invite link

The link format is `<site>/join?c=<circleId>&t=<token>`. The join page:
1. Calls `POST /circles/{c}/join` with `{ "token": t }` and no auth header.
2. Stores `sessionToken` and `circleId`.
3. Calls `GET /circles/{circleId}` to get `activePlanId`.

A used or expired invite returns 404. Show "This invite link has already been used or expired. Ask for a new one."

### What to persist (localStorage is fine)

- **Owner:** `circleId` (from `POST /circles`), plus the current `planId` (from extract).
- **Caregiver:** `sessionToken` and `circleId`.
- **Both:** fetch `GET /circles/{circleId}` on app start to learn `activePlanId`, `language`, `slotTimes` and `role`.

There is no "list my circles" endpoint. An owner on a new device has to create a new circle. That's acceptable for the demo.

## 4. Screens and the calls behind them

### 4.1 Setup (owner, first run)

- Sign in, then call `POST /circles` with `{ name, language }`. `language` is one of `en | hi | kn`, default `kn`. The response is `{ circleId }`; store it.
- Invite a caregiver: `POST /circles/{circleId}/invite` returns `{ token, url, expiresAt }`. Show `url` as a share button and a QR code (generated client-side). The invite is single use and lasts 24 hours.

### 4.2 Upload the discharge summary (owner)

1. `<input type="file" accept="image/jpeg,image/png" capture="environment">`. Use the native camera, not a camera library. Support multiple pages (1 to 10) with thumbnails and an "add page" button.
2. `POST /documents` with `{ circleId, pageCount, contentType }`. `contentType` is `image/jpeg` or `image/png` only; **PDF is not supported.** All pages in one document share one content type.
3. The response is `{ documentId, uploads: [{ page, key, uploadUrl }] }`. `PUT` each file's bytes to its `uploadUrl` with header `Content-Type` **exactly equal** to the `contentType` you sent. Any mismatch returns S3 `SignatureDoesNotMatch`. Upload links expire in 15 minutes.
4. `POST /documents/{documentId}/extract` with `{ circleId }`. **This takes 20 to 120 seconds.** Show a progress state that survives that long ("Reading the prescription..."), and set the fetch timeout to at least 130 s.
5. The response is a draft `Plan`. Go to Review.

About extract:
- It is idempotent: calling it again for the same document returns the same plan without re-reading.
- `422 extraction_failed` means the photo could not be read (blurry, cut off, or upload missing). Offer "Retake photo".
- Keep the uploaded `File` objects in memory; Review needs them for the crops (see 4.3).

### 4.3 Review and confirm (owner) — the most important screen

- One card per medicine: brand, molecules (name, strength, unit), frequency, slots, food, duration, and `rawText`.
- **Always show `rawText`.** It's the exact words read from the paper, and it's how the family checks us.
- **Source crop:** `medicine.crop` is `{ x, y, w, h, s3Key }`. The rect is normalised 0 to 1, and `s3Key` ends in `p<n>.<ext>`, which tells you the page number. Render it as a CSS `background-image` window over the **local** file for that page (`background-size` and `background-position` computed from the rect). The S3 bucket is private, so there is no image URL to fetch. After a reload, fall back to `rawText` only. `crop` may be null; then show `rawText` only.
- **`null` means "not written on the paper".** Show "Not written, ask your doctor". Never fill a value in.
- `needsConfirmation: true` shows the card as amber, with an icon and the word "Check this". The Activate button stays disabled until no amber cards remain.
  - **To confirm an unchanged card:** send `PATCH /plans/{planId}` with the full `medicines` array, that line's `needsConfirmation: false`, and `userEdited: false`.
  - **To edit a strength, frequency, slots or duration:** send `userEdited: true`. If you edit frequency, also send the `slots` the user picked (tap the morning, noon, night and bedtime dots). The backend never derives slots on edit, and a line with slots but no frequency is rejected.
  - **To add a line:** `source: "user"`, empty `sourceBlockIds`, `userEdited: true`.
- `PATCH` body: `{ circleId, medicines, userEdited, language?, slotTimes? }`. It returns the updated `Plan`. `422 validation_failed` carries a readable `message`; show it.
- **Activate:** `POST /plans/{planId}/activate` with `{ circleId }` returns `{ planId, status, dosesCreated, firstDoseAt }`. It creates 7 days (or the written duration) of doses and schedules reminders. A 409 means it's already active. Slots that have already passed today are skipped.

### 4.4 Schedule (main screen, both roles)

- Get the plan with `GET /plans/{planId}` (owner adds `?circleId=`).
- **Grid:** rows are medicines, columns are `morning | noon | night | bedtime`. Default times come from `slotTimes` (08:00, 14:00, 20:00, 22:00 IST).
- Show a filled dot for "take" and an empty dot for "skip". Use a plate icon with a word for before or after food.
- **One "Given" button per slot, not per medicine.** Each dose record covers every medicine due in that slot.
- **Today's dose status:** `GET /plans/{planId}/adherence?days=1` returns `{ doses: Dose[], givenPct }`, where `Dose` is `{ doseId, date, slot, status, givenAt, givenBy, medicineLineIds }`. `status` is `pending | given | missed`.
- **Mark given:** `POST /doses/{doseId}/given`, where `doseId` looks like `ci_demo#2026-09-18#morning`.
  - **URL-encode it** with `encodeURIComponent`, because `#` breaks URLs otherwise.
  - The call is idempotent, so a retry returns the same record.
  - A `missed` dose can still be marked given later.
- **Offline:** cache the active plan in the service worker, queue Given taps keyed by `doseId`, and replay them when back online.
- **PRN medicines** (`prn: true`, no slots) go in a separate "Only when needed" section with `prnCondition`.
- `durationDays: null` shows "Duration not written. Ask your doctor."
- **Speaker button:** `GET /plans/{planId}/audio?lang=kn|hi|en` returns `{ url, spokenLanguage, text }`. Play `url` in an `<audio>` element; it's a presigned mp3. Kannada comes back as Hindi audio, because Polly has no Kannada voice. Show `text` as captions.

### 4.5 Box Check (both roles)

1. Photograph the medicine strips. The upload flow is the same as 4.2 (`POST /documents` and the PUTs), with one page per photo. Caregivers are allowed to do this.
2. `POST /boxcheck` with `{ circleId, planId, documentId }`. This takes 10 to 40 seconds, so show a progress state.
3. The response is `{ items: BoxCheckItem[] }`, where each item is `{ verdict, reason, message, prescribedLineId, stripBrandText, stripMolecules }`:
   - `matched`: green, tick icon, the word "Matches".
   - `check`: amber, warning icon, the word "Check".
   - `do_not_take`: red, stop icon, the words "Do not take".
4. **Show `message` exactly as returned.** Never write your own verdict copy, and never use the word "safe".

### 4.6 Red flags (both roles)

- Show `plan.redFlags.text` verbatim.
- `source: "document"` means "From your discharge summary".
- `source: "generic"` gets a visible band: "General advice, not from your document."
- There's no crop for red flags. Never add client-written warnings.

### 4.7 Fridge sheet

Render the schedule grid to a `<canvas>`, export it as PNG, and trigger a download plus the Web Share sheet. It must be readable printed in black and white, so use shapes and words rather than colour.

### 4.8 Push notifications and install

- The service worker plus `app/manifest.ts` follow the official Next.js PWA guide.
- Ask for notification permission **only after a user tap**. On iOS Safari, show Add to Home Screen instructions first, because iOS only allows push from an installed PWA.
- Subscribe with `applicationServerKey = NEXT_PUBLIC_VAPID_PUBLIC_KEY`, then `POST /circles/{circleId}/push` with `{ subscription: sub.toJSON() }`. It returns 204.
- Pushes arrive as JSON `{ "title": "...", "body": "..." }`. In the service worker `push` handler, call `showNotification(title, { body })`. Clicking the notification opens the schedule.
- Reminders fire at each slot time. If the dose isn't marked given within the circle's `escalationMinutes` (30 by default, 60 on the demo), it becomes `missed` and everyone in the circle gets an escalation push, plus email for owners.

### 4.9 Family view (read-only, for relatives far away)

The read-only schedule plus `GET /plans/{planId}/adherence?days=7`: a list of the last 7 days, newest first, with `givenPct` shown as "X% of doses given".

## 5. Errors

Every error body is `{ code, message }`.

| HTTP | code | Show |
|---|---|---|
| 401 | unauthorized | Sign in again (owner) or ask for a new invite (caregiver) |
| 403 | forbidden | "You don't have access to this." |
| 404 | not_found | Context-specific (plan missing, invite used) |
| 409 | conflict | Already active: just reload |
| 422 | validation_failed | Show `message` |
| 422 | extraction_failed | "We couldn't read this photo. Retake it in good light, flat, whole page in frame." |
| 503 | auth_unavailable | "Sign-in check is down, try again in a minute." |

## 6. UI and safety rules (non-negotiable)

- Body text at least 18px. Primary buttons at least 56px tall with text of 20px or larger. Contrast about 7:1 for use in sunlight.
- A bottom bar with Schedule, Box Check and Red flags. No hamburger menu.
- Self-host Noto Sans Kannada and Noto Sans Devanagari. No CDN fonts.
- Every state has an icon **and** a word. Never use colour alone.
- Footer on every screen: *AfterCare re-displays what your doctor wrote. It never changes a dose.*
- No analytics or third-party scripts. Never `console.log` document text, medicine names, tokens or emails.
- The client never invents a medical value, a verdict message or a warning.

## 7. Known limits (don't build around these, just be aware)

1. No PDF upload; photos only.
2. No list of circles for an owner, so persist `circleId` locally.
3. Crops only work while the uploaded files are still in memory.
4. Box Check compares salt names literally. "Ferrous ascorbate" on the prescription against "elemental iron" on the strip shows "check with your chemist", even though they're the same drug. This is conservative by design and not a bug to work around.
5. SES sandbox: login emails reach verified addresses only.
6. WhatsApp is built but switched off.

## 8. Suggested structure

```text
web/
  app/  page.tsx (entry), join/, setup/, upload/, review/, schedule/, box-check/,
        red-flags/, fridge-sheet/, family/, layout.tsx, manifest.ts
  components/
  lib/  api/client.ts, api/types.ts (generate from openapi.yaml, e.g. openapi-typescript),
        auth/session.ts, offline/queue.ts
  public/ fonts/, icons/, sw.js
```

## 9. Definition of done

- `npm run build` produces a static export, and `npm run lint` passes.
- Owner flow works live end to end: sign in, create circle, upload, extract, review and confirm, activate, schedule, mark given.
- Caregiver flow works live: invite link, join, schedule, mark given, Box Check, audio.
- Activate is impossible while amber cards remain.
- Push works on Android Chrome and on installed iOS.
- Every verdict and safety text comes from the API or the fixed copy above.
