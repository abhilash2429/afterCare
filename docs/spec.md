# AfterCare — System Design & Specification

**Version:** 1.0 (frozen 2026-09-18)
**Event:** First Commit — WeMakeDevs x AWS Bharat Builds Tour, 17–20 Sep 2026
**Track:** Ship It (deployed on AWS, public URL)
**Region:** ap-south-1 (Mumbai) for everything except Bedrock inference

---

## 1. Problem

A patient is discharged from an Indian hospital with a two-page summary written in
clinical shorthand: `T. Ecosprin 75 OD after food x 30 days`, `Tab Pan 40 BD before
food`, `Clopitab 75 HS`. The person who actually administers those medicines at home
is a spouse or parent who may not read English.

Measured consequences in Indian studies:

- Only **31%** of public-hospital discharge notes contain diagnosis + medication +
  lifestyle + follow-up; only **25%** of patients/carers show good understanding
  (PLOS ONE, doi:10.1371/journal.pone.0230438).
- **27%** of paediatric caregivers do not understand medication directions and
  **70%** do not comply (doi:10.1016/j.cegh.2022.101137).
- **36.8%** of OPD patients had poor composite understanding of their prescription;
  they asked for vernacular and pictorial formats (doi:10.4103/ijp.ijp_359_24).
- Colour-coded/pictorial dosing charts measurably improve understanding among
  non-readers (JSSRP, doi:10.4103/jssrp.jssrp_2_26).

**The gap nobody covers:** every existing product (Layrd, Abridge, hospital EMRs)
turns clinical documents into structure *for the doctor*. Medisafe-style reminder
apps assume the user can already read the prescription. Nothing takes the paper the
family was handed and renders it for the person holding the pill box, in their
language, and then checks that the pills in the box actually match the paper.

## 2. Product

**One line:** photograph the discharge summary, get a picture-and-voice medicine
schedule in your language, then photograph the strips you bought to confirm the box
matches the paper.

**Personas**

| | |
|---|---|
| **Shanta, 64, Hubli** | Primary user. Reads Kannada, some Hindi, little English. Holds the phone and the pill box. Taps one button per dose slot. Never types a password. |
| **Arjun, 31, Bangalore** | Son. Sets the account up, uploads the summary, confirms the extraction, receives escalations. |

**Demo case:** post-cardiac-event discharge — 5 to 7 medicines, brand confusion
(Ecosprin / Clopitab / Atorva), a genuine duplicate-molecule risk, and red flags
where getting it wrong kills.

**Product rule, absolute:** AfterCare re-displays what the doctor wrote. It never
changes a dose, never suggests a substitute, never infers a warning the document
does not contain. Anything it cannot determine is rendered as **"ask doctor"**,
never guessed.

## 3. Scope

### v1 (must work in the demo video)

1. **Extraction with source crops** — every extracted field shows the crop of the
   original image it came from; low-confidence fields are blocked until confirmed.
2. **Picture schedule + voice** — slot grid (morning / noon / night / bedtime),
   food-relation icon, Kannada text, Hindi audio.
3. **Red-flag card** — verbatim from the document, or a clearly-labelled generic card.
4. **Box Check** — photograph strips, match them to the prescription by molecule.
5. **Missed-dose escalation** — Web Push to Shanta, WhatsApp + email to Arjun.
6. **Fridge sheet** — client-rendered PNG of the schedule, shareable on WhatsApp.

### Stretch, in order

7. Duplicate-molecule flag across multiple documents.
8. Refill countdown ("Metformin runs out Thursday").

### Explicitly out of scope

Handwritten prescriptions · a chatbot that answers questions about medicines ·
Jan Aushadhi price substitution · daily voice check-in calls · SMS of any kind ·
iOS-native anything · multi-tenant hospital deployment.

### Cut order under time pressure

WhatsApp escalation (email covers it) → Arjun's adherence log → Cognito and the care
circle entirely (single-device demo) → Box Check *extra-strip* detection (keep
matched + missing). **Box Check itself is never cut** — without it this is just
another prescription reader.

## 4. Architecture

```
                         Amplify Hosting (Next.js 15, static export, PWA)
                                        │  HTTPS + JWT
                                        ▼
                         Lambda Function URL  ── api (Python 3.12)
                                 │
     ┌───────────────┬───────────┼────────────┬─────────────────┐
     ▼               ▼           ▼            ▼                 ▼
  S3 (docs)      Textract    Bedrock      DynamoDB       EventBridge Scheduler
  SSE-KMS      words+boxes   Mistral L3   single table    one-time per dose slot
  30d expiry    LAYOUT       (in-region)  + drugs table          │
                             Nova Lite                           ▼
                                │                        reminder Lambda
                             Translate                          │
                             Polly (Kajal, hi-IN)        ┌──────┴──────┐
                                                          ▼             ▼
                                                     Web Push      escalate:
                                                    (pywebpush)    WhatsApp (EUM Social)
                                                                  + SES email
                                       Cognito user pool (email OTP, Essentials)
```

### Why a Lambda Function URL instead of API Gateway

Extraction runs Textract then Bedrock on multi-page documents and regularly exceeds
API Gateway HTTP API's hard **29-second** integration timeout. A Function URL allows
up to the Lambda 15-minute limit. A single entry point also means one CORS config,
one JWT verification path, one deployment unit. We verify Cognito JWTs in code
against the pool's JWKS rather than using an API Gateway authorizer.

**Trade-off accepted:** no built-in throttling, WAF or usage plans. For a 3-day build
with a private demo audience that is the correct trade; the migration path to HTTP
API is a CDK change plus moving JWT verification into an authorizer.

### Region and residency

Everything that stores data — S3, DynamoDB, Cognito, Scheduler, SES, WhatsApp — runs
in **ap-south-1**. Health data at rest never leaves India.

Extraction runs on **Mistral Large 3** (`mistral.mistral-large-3-675b-instruct`),
an on-demand Bedrock model served **in ap-south-1**, so document inference stays in
India too. It won the Task 9 golden-set bake-off against Nova Pro (APAC profile) and
Qwen3-VL 235B: it was the most accurate model to pass every gate. Anthropic and OpenAI
models are out: they need an AWS Marketplace agreement, which this project does not take.

Polly generative voices do not exist in Mumbai; we use the **neural Hindi voice
Kajal**, which does.

### Model roles

| Job | Model | Why |
|---|---|---|
| Document → structured plan | Mistral Large 3 (on-demand, ap-south-1) | Won the golden-set bake-off; in-region |
| Strip photo → brand/composition | Mistral Large 3 | Same vision path, small images |
| Verdict/summary phrasing | Nova Lite (APAC) | Cheap, low-risk text |
| Translation | Amazon Translate | Deterministic, no model risk |

Exact Bedrock inference-profile IDs are resolved at build time with
`aws bedrock list-inference-profiles` and stored in `infra/config.py`. They are never
hard-coded from memory.

## 5. Extraction pipeline

```
image/PDF → S3
   │
   ├─ Textract AnalyzeDocument [TABLES, LAYOUT]
   │     → WORD blocks with Id + BoundingBox (normalised 0–1)
   │     → LAYOUT_* blocks for section detection
   │
   ├─ Bedrock Mistral Large 3 (Converse API, image + the Textract word list with IDs)
   │     → strict JSON: medicines[], red_flags, follow_up
   │     → every field carries source_block_ids[] and confidence 0–1
   │
   └─ crop service: block IDs → union bounding box → crop rect
         stored as {documentId, page, x, y, w, h} — the crop is rendered
         client-side from the original image, no second S3 object
```

**Textract only reads Latin script** (English, Spanish, German, Italian, French,
Portuguese). Printed Indian prescriptions are effectively always English, so this is
acceptable. If Textract returns fewer than 20 WORD blocks for a page, we fall back to
Bedrock vision reading the raw image and mark every field on that page
`source: "vision_only"`, which disables crops for those fields and forces confirmation.

**Confidence gate:** any field with confidence < 0.85, or any field the model marks
`"ask doctor"`, is rendered in amber and blocks plan activation until the user taps it.

### Plan JSON (the contract between extraction and everything else)

```json
{
  "planId": "pl_01J...",
  "circleId": "ci_01J...",
  "patientName": "REDACTED_BY_USER",
  "sourceDocumentIds": ["doc_01J..."],
  "medicines": [
    {
      "lineId": "m1",
      "rawText": "T. Ecosprin 75 OD after food x 30 days",
      "brand": "Ecosprin",
      "molecules": [{"name": "Aspirin", "strengthMg": 75}],
      "form": "tablet",
      "frequency": "OD",
      "slots": ["morning"],
      "foodRelation": "after",
      "durationDays": 30,
      "prn": false,
      "prnCondition": null,
      "confidence": 0.94,
      "sourceBlockIds": ["b12", "b13", "b14"],
      "needsConfirmation": false
    }
  ],
  "redFlags": {
    "source": "document",
    "text": "Report immediately if chest pain, breathlessness or bleeding.",
    "sourceBlockIds": ["b81"]
  },
  "followUp": {"date": "2026-10-02", "with": "Cardiology OPD", "confidence": 0.9},
  "status": "draft"
}
```

`redFlags.source` is `"document"` or `"generic"`. Nothing else is permitted. The
generic card carries the fixed text in §7 and is visually marked as not from the
document.

## 6. Schedule engine

Deterministic pure function, no model involved.

| Input | Output |
|---|---|
| `OD` | `["morning"]` |
| `BD` | `["morning", "night"]` |
| `TDS` / `TID` | `["morning", "noon", "night"]` |
| `QID` | `["morning", "noon", "night", "bedtime"]` |
| `HS` / `nocte` | `["bedtime"]` |
| `SOS` / `PRN` | `[]` — never scheduled, shown in an "only when needed" row |
| `1-0-1` | `["morning", "night"]` (positional: morning-noon-night) |
| `1-1-1-1` | all four |

Default slot times, editable per circle: morning 08:00, noon 14:00, night 20:00,
bedtime 22:00. All times are IST (`Asia/Kolkata`); schedules are created in UTC.

`durationDays` sets the end date. If absent, we schedule **7 days** and label the
medicine "duration not stated — ask your doctor".

**Dose granularity:** one dose record per *slot per day*, not per medicine. Shanta
taps **Given** once for the whole 08:00 slot. This matches how medicines are actually
administered from a pill box and cuts taps by 5x.

A slot is **missed** if no `given` arrives within the circle's escalation window
(default 60 minutes) after the reminder.

## 7. Safety rules (non-negotiable)

These are enforced in code, not only in prompts. Prompt-only enforcement is not
acceptable for any of them.

1. **No dose modification.** The API rejects any plan write where a molecule's
   `strengthMg` or `frequency` differs from the extracted value unless the request
   carries `"userEdited": true` and an audit record of who changed it.
2. **No invented red flags.** `redFlags.source == "document"` requires non-empty
   `sourceBlockIds`. The API rejects the plan otherwise.
3. **Generic red-flag text is a constant**, never generated:
   > "Call your doctor or 108 immediately for: chest pain, breathlessness, heavy
   > bleeding, fever above 101°F, fainting or confusion. This is general advice —
   > it was not found in your document."
4. **No filled-in gaps.** A missing frequency, strength or duration is `null` plus
   `needsConfirmation: true`. The prompt forbids inference and the validator rejects
   any medicine with a non-null value and empty `sourceBlockIds`.
5. **Bedrock Guardrail** on the extraction and phrasing models: denied topics cover
   dosage advice, substitution advice and diagnosis. This is the second layer, not
   the first.
6. **Box Check never says "safe to take".** Its language is "matches your
   prescription" / "check with your chemist" / "do not take — ask your doctor".
7. Every screen carries the disclaimer: *AfterCare re-displays what your doctor
   wrote. It never changes a dose.*

## 8. Box Check

```
strip photos → Bedrock vision → [{brandText, compositionText, strengthText}]
                                        │
                     ┌──────────────────┴───────────────────┐
                     ▼                                      ▼
        brand → molecule via drugs table          composition text printed
        (prefix bucket + rapidfuzz ≥ 88)          on the strip (legally
                     │                            mandated in India)
                     └──────────────────┬───────────────────┘
                                        ▼
                        compare against plan.medicines[].molecules
```

| Verdict | Condition | Copy |
|---|---|---|
| **Green — matched** | molecule and strength both equal a prescribed medicine | "This is your Ecosprin. Same medicine, different brand name." |
| **Amber — check** | molecule matches, strength differs · strip is a combination containing the prescribed molecule plus others · brand unreadable but molecule matches | "Check with your chemist before using." |
| **Red — do not take** | a prescribed medicine has no strip in the box (missing) · a strip maps to no prescribed molecule (extra) · the strip duplicates a molecule already prescribed under another brand | "Do not take this until you ask your doctor." |

Brand names are matched *after* the printed composition, not before. The drug dataset
is from 2022 and will miss newer brands; the composition printed on the strip will
not. The dataset is a convenience, not the source of truth.

**Data source:** Kaggle *A-Z Medicine Dataset of India* (~250K SKUs, CC BY-SA 4.0),
joined with *Extensive A-Z Medicines Dataset* (MIT) for `substitute*` and drug-class
columns. Attribution goes in the README and on the About screen.

**Lookup design:** DynamoDB `aftercare-drugs`, `PK = first 4 chars of normalised
brand`, `SK = full normalised brand`. Query the bucket, then `rapidfuzz` the
candidates. No full-table scan, no 250K-row load into Lambda memory.

## 9. Data model

**Table `aftercare`** (single table, on-demand, PITR off, TTL on `expiresAt`)

| PK | SK | Item |
|---|---|---|
| `CIRCLE#<cid>` | `META` | name, language, slotTimes, escalationMinutes |
| `CIRCLE#<cid>` | `MEMBER#<userId>` | role (`owner` / `caregiver`), email, pushSubscription, whatsappNumber |
| `CIRCLE#<cid>` | `PLAN#<planId>` | the full plan JSON of §5 |
| `CIRCLE#<cid>` | `DOSE#<yyyy-mm-dd>#<slot>` | status (`pending`/`given`/`missed`), givenAt, givenBy, medicineLineIds |
| `CIRCLE#<cid>` | `DOC#<documentId>` | s3Key, pageCount, uploadedBy, textractCacheKey |
| `INVITE#<token>` | `META` | circleId, role, expiresAt (TTL, 24h) |

**Table `aftercare-drugs`** — `PK` brand prefix, `SK` normalised brand, attrs:
`brand`, `molecules[]`, `manufacturer`, `packSize`, `discontinued`.

**S3 `aftercare-docs-<account>-ap-south-1`** — `circles/<cid>/<documentId>/p<n>.jpg`,
SSE-KMS (aws/s3 managed key), block all public access, **lifecycle expiry 30 days**,
CORS allowing PUT from the Amplify origin only.

## 10. Auth and the care circle

- **Cognito user pool**, Essentials tier, **passwordless email OTP**
  (`USER_AUTH` + `preferredChallenge: EMAIL_OTP`). SMS OTP is impossible — Indian
  local-route SMS requires TRAI DLT registration with a company PAN, GSTIN and CIN.
- **Arjun** signs in with an email code and creates the circle.
- **Shanta never signs in.** Arjun generates a single-use invite token (QR or link).
  Her device exchanges it once for a long-lived circle session token (JWT signed by
  our own key, 90 days, scoped to `circleId` + role `caregiver`). She sees the
  schedule, taps Given, runs Box Check. She cannot edit the plan.
- Every API handler resolves `(principal, circleId, role)` before touching data.
  Role `caregiver` is denied on `PATCH /plans/*` and `POST /plans/*/activate`.

## 11. Notifications

| Event | Shanta | Arjun |
|---|---|---|
| Dose due | Web Push | — |
| Slot missed (after window) | Web Push repeat | WhatsApp + SES email |
| Plan activated | — | SES email summary |

- **Web Push** via `pywebpush` with VAPID keys in Secrets Manager. iOS 16.4+ requires
  the PWA to be **installed to the Home Screen** and the permission prompt to be
  triggered by a user tap; Android Chrome works without installing. The onboarding
  screen detects iOS Safari and shows Add-to-Home-Screen instructions.
- **WhatsApp** via AWS End User Messaging Social (`socialmessaging`) in ap-south-1.
  Business-initiated messages outside the 24-hour window require a **Meta-approved
  message template** — submit it on day 1. The number used must not already be
  registered on the WhatsApp app.
- **SES** is in sandbox: verified recipients only, 200 messages/24h. Verify both
  teammates' addresses; that is sufficient for the demo. Production access is
  requested but not depended on.

**Delivery is best-effort with a fallback chain:** WhatsApp → SES → in-app banner.
A failed channel is logged and never blocks the dose flow.

## 12. Privacy

- Raw document images auto-delete after **30 days** (S3 lifecycle).
- No document text, medicine names or email addresses in CloudWatch logs — IDs only.
  A shared `redact()` helper is the only logging path for user-derived data.
- Bedrock does not train on inputs (AWS default) — stated on camera.
- **Delete my data** wipes every item under `CIRCLE#<cid>` plus the S3 prefix, and is
  reachable in two taps from Settings.
- No analytics, no third-party scripts, no ad tech in the PWA.
- Test documents contain no real patient data: they are generated from the blank
  NABH E-Mitra discharge summary template and filled with synthetic patients.

## 13. Frontend

**Next.js 15** (Amplify Hosting supports 12–15; 16 is unverified, so it is pinned),
App Router, **`output: 'export'`** static export, TypeScript, Tailwind.

All data is fetched client-side from the Function URL. There is no SSR layer, no
server actions, no edge runtime — all of which are either unsupported on Amplify or
add a second compute tier for no benefit.

**Design constraints (this is the Best UI entry):**

- Minimum body text 18px, primary actions 20px+ and at least 56px tall.
- Three colours carry meaning and nothing else does: green (given / matched), amber
  (confirm / check), red (missed / do not take). Never colour alone — every state
  carries an icon and a word.
- No hamburger menu. Bottom bar with three targets: Schedule · Box Check · Red flags.
- Works one-handed in bright sunlight: high contrast, no thin greys, no hover-only
  affordances.
- Kannada and Hindi glyphs need `Noto Sans Kannada` / `Noto Sans Devanagari`
  self-hosted, not a CDN font that may be blocked.
- Offline: the service worker caches the active schedule so the grid renders with no
  network. Marking Given queues and syncs.

**Screen order of build:** Upload → Review & Confirm → Schedule → Box Check →
Red flags → Fridge sheet → Arjun's view → Settings → Circle/Invite → Sign-in.
The last two are faked with a URL parameter until Cognito is wired.

## 14. API surface

Full contract in `docs/api/openapi.yaml`, frozen before implementation. The frontend
is developed against a Prism mock generated from that file and is never blocked on
backend progress.

```
POST   /documents                  → {documentId, uploadUrl}   presigned S3 PUT
POST   /documents/{id}/extract     → draft plan  (long-running, up to 120s)
GET    /plans/{id}                 → plan
PATCH  /plans/{id}                 → apply corrections (owner only)
POST   /plans/{id}/activate        → creates dose records + Scheduler schedules
POST   /doses/{doseId}/given       → mark a slot given
GET    /plans/{id}/adherence       → dose log
POST   /boxcheck                   → strip photos in, verdicts out
POST   /circles/{id}/invite        → {token, qrPayload, expiresAt}
POST   /circles/{id}/push          → register a Web Push subscription
GET    /health                     → {ok: true, commit}
```

## 15. Quality gate

A 10-document golden set lives in `data/golden/`, generated from the NABH template
with hand-written expected JSON. `pytest -m golden` scores field-level accuracy.

| Field | Ship gate |
|---|---|
| drug name | ≥ 90% |
| strength | ≥ 90% |
| frequency → slots | ≥ 80% |
| food relation | ≥ 80% |
| duration | ≥ 80% |

The same harness runs the model bake-off (`scripts/bakeoff.py <model_id> ...`). A model
must pass every gate; among passers the highest mean accuracy wins; within 2 points
in-region on-demand is preferred, then price. Task 9 result: Mistral Large 3.

## 16. Cost

| Service | Demo-scale estimate |
|---|---|
| Textract (Tables + Layout) | $0.015/page → ~$1.50 for 100 test pages |
| Bedrock Mistral Large 3 | ~4k input + ~2k output tokens per page extracted |
| Lambda, DynamoDB on-demand, S3, Scheduler | pennies; all scale to zero |
| Cognito Essentials | free below 10K MAU |
| Amplify Hosting | free tier |
| **Total for the hackathon** | **well under $20 of the $200 credit** |

A `$50` AWS Budgets alarm is created on day 1. Fixed monthly cost at zero users is
**$0** — nothing here is provisioned capacity.

## 17. Risks

| Risk | Mitigation |
|---|---|
| Live extraction fails while recording | Seeded demo circle behind a URL flag; same code path, pre-populated state. Record the risky live scan once, everything downstream from the seed. |
| Meta rejects the WhatsApp display name or template | SES email fallback already in the chain; cut per §3. |
| Textract misses a page layout | Bedrock-vision fallback path, fields marked `vision_only` and forced to confirm. |
| Drug dataset is from 2022 | Composition printed on the strip takes priority over the brand lookup. |
| Amplify + Next.js 16 incompatibility | Pinned to Next.js 15. |
| Teammate blocked on backend | OpenAPI frozen first, Prism mock from hour one. |
| Bedrock model ID guessed wrong | Resolved from `list-inference-profiles` at build time, never from memory. |
| Time | Hard freeze Sunday 14:00 IST. Video and writeup only after that. |

## 18. Judging alignment

| Criterion | Where we win |
|---|---|
| Idea & Impact | Indian clinical evidence with numbers; the caregiver, not the doctor |
| Built on AWS | Textract, Bedrock, Translate, Polly, Lambda, DynamoDB, S3, Scheduler, Cognito, SES, End User Messaging Social, Amplify — shown in the console on camera |
| Learning | First Bedrock Guardrail, first EventBridge Scheduler, first CDK stack, first End User Messaging Social — stated explicitly on camera |
| Execution | One flow works end to end: paper → schedule → box → escalation |
| Demo video | Physical artefacts: a printed summary, a pill box, two phones |

**The line that separates us from every other prescription reader:**
*Everyone reads the prescription. We check that the paper matches the pill box.*

## 19. Delivery

Monorepo, deployed from a laptop, no CI (3 days).

```
infra/   CDK (Python)      — one stack, ap-south-1
api/     Lambda handlers   — Python 3.12 runtime (local dev on 3.11: no 3.12-only syntax)
web/     Next.js 15 PWA    — Amplify Hosting from main
data/    drug ETL + golden set
docs/    this spec, the plan, openapi.yaml
```

Backend deploys with `cdk deploy` from your machine. Frontend auto-deploys from
`main` via Amplify. Commit small and often — judges check that repo history matches
the event dates, and this repository's first commit is dated after the clock started.

**Team:** you own backend and infra (with coding agents). Your teammate owns the
Next.js frontend, the demo video and the Builder Center writeup.

**Both members must have verified student status on AWS Builder Center.** The
submission deadline time was not yet published as of 2026-09-18 — check the
hackathon page daily.
