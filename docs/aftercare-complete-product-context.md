# AfterCare complete product context

This is the full product and engineering brief for AfterCare. It combines the product specification, implementation plan, API contract, current repository behavior, deployment design, demo plan, and frontend requirements.

Checked against the repository on September 18, 2026.

## 1. Product identity

Product name: AfterCare

One-line description:

Photograph an Indian hospital discharge summary, receive a picture-and-voice medicine schedule in the caregiver's language, then photograph the medicine strips to check that the pill box matches the paper.

Product thesis:

Everyone reads the prescription. AfterCare checks that the paper matches the pill box.

The product exists for the person who is physically holding the medicine box at home. Most clinical-document systems structure information for doctors. Most reminder apps assume the user can already understand the prescription. AfterCare is designed for the patient or family member who may read little English and needs an understandable, visual, cautious representation of the doctor's instructions.

Absolute product promise:

AfterCare re-displays what the doctor wrote. It never changes a dose, suggests a substitute, or invents a warning. When a value cannot be determined, the product shows ask doctor and blocks activation until the user confirms it.

Event context:

- Event: First Commit, WeMakeDevs x AWS Bharat Builds Tour
- Track: Ship It
- Event dates in the repository: September 17 to 20, 2026
- Planned hard freeze: Sunday, September 20, 2026 at 14:00 IST
- Deployment region: ap-south-1, Mumbai, except for the declared Bedrock inference behavior
- Build shape: three-day hackathon monorepo, deployed from a laptop, with no CI requirement

## 2. Problem being solved

The starting document is an Indian hospital discharge summary or prescription written in clinical shorthand, for example:

~~~text
T. Ecosprin 75 OD after food x 30 days
Tab Pan 40 BD before food
Clopitab 75 HS
~~~

The person administering medicines may be a spouse, parent, or older patient who does not comfortably read English. The family also has to map a brand name on a purchased strip to the molecule named or implied by the prescription.

The repository cites these problem signals:

- A PLOS ONE study cited by the project reports that only 31 percent of Indian public-hospital discharge notes contain diagnosis, medication, lifestyle, and follow-up information, and only 25 percent of patients or carers show good understanding.
- A paediatric-caregiver study cited by the project reports 27 percent did not understand medication directions and 70 percent did not comply.
- An OPD study cited by the project reports 36.8 percent poor composite understanding and demand for vernacular and pictorial formats.
- The specification cites evidence that colour-coded and pictorial dosing charts improve understanding among non-readers.

These figures are product justification in the repository. They are not runtime inputs and the application does not present them to patients during medication use.

## 3. Users and roles

### Shanta

- Age and location in the demo persona: 64, Hubli
- Reads Kannada, some Hindi, and little English
- Holds the phone and pill box at home
- Needs large controls, visual slot cues, food icons, voice playback, and no password entry
- Uses the caregiver session created from an invite link
- Can view the active schedule
- Can mark a dose slot as given
- Can run Box Check
- Can receive Web Push reminders
- Cannot edit or activate a plan

### Arjun

- Age and location in the demo persona: 31, Bangalore
- Son and setup operator
- Signs in with a passwordless email OTP through Cognito
- Creates the care circle
- Uploads the discharge summary
- Reviews and confirms the extraction
- Activates the plan
- Generates a one-time caregiver invite
- Receives missed-dose escalations by WhatsApp and SES email
- Can view adherence

### Owner

The backend role for the signed-in setup user. The owner is represented by a Cognito ID token and must be recorded as an owner member of the circle before accessing that circle's data.

### Caregiver

The backend role for the invite recipient. The caregiver uses a signed AfterCare session token scoped to one circle for 90 days. The token is exchanged once from the invite URL and does not require a Cognito login.

## 4. Main product flow

The intended end-to-end flow is:

1. Arjun signs in with an email OTP.
2. Arjun creates a care circle, normally using the default name Family and Kannada as the default language.
3. Arjun photographs one or more pages of the discharge summary.
4. The browser requests document upload URLs from the API.
5. The browser uploads each page directly to private S3 using its presigned URL.
6. The browser requests extraction.
7. Textract reads words and layout, then Bedrock structures medicines, red flags, and follow-up data.
8. Every extracted value carries confidence and source information.
9. The Review and Confirm screen shows each medicine and its source crop when available.
10. Low-confidence or unresolved values are marked amber and block activation.
11. Arjun confirms or explicitly edits the plan. A strength or frequency edit sets userEdited to true.
12. Arjun activates the plan.
13. The backend creates one dose record per slot per day and schedules reminders.
14. Arjun generates an invite URL or QR payload.
15. Shanta opens the invite URL containing the circle ID and one-time token.
16. The browser exchanges the token for a 90-day caregiver session token.
17. Shanta sees the picture schedule in the selected language.
18. Shanta taps Given once for each shared dose slot.
19. The browser can queue Given actions while offline and sync them later.
20. The reminder system sends Web Push when a dose is due.
21. If the dose remains unmarked after the escalation window, the system repeats Web Push to Shanta and escalates to Arjun through WhatsApp and SES email.
22. Shanta photographs purchased strips.
23. The browser uploads the strip photos as a document.
24. Box Check maps strip composition to prescribed molecules and returns matched, check, or do-not-take verdicts.
25. The schedule can be rendered as a black-and-white fridge-sheet PNG.

## 5. Version 1 scope

These are the features intended to work in the demo video:

1. Extraction with source crops. Every extracted field should be traceable to its source page and text region when the extraction path supports it.
2. A picture schedule with morning, noon, night, and bedtime slots.
3. Food relation icons for before food and after food.
4. Kannada display text and Hindi schedule audio.
5. A red-flag card. It is either verbatim from the document or visibly marked as generic advice.
6. Box Check. Strip photos are compared to the active prescription by molecule and strength.
7. Missed-dose escalation. Web Push goes to Shanta. WhatsApp and email go to Arjun.
8. A client-rendered fridge sheet that can be downloaded or shared.

## 6. Stretch scope

The stretch items are ordered:

1. Duplicate-molecule detection across multiple documents.
2. Refill countdown, such as Metformin runs out Thursday.

The current pure Box Check engine already detects duplicate molecules inside one plan. Cross-document duplicate detection and refill countdown are not part of the planned v1 implementation.

## 7. Explicitly out of scope

The product must not expand into these areas during the hackathon:

- Handwritten-prescription support
- A chatbot that answers medicine questions
- Jan Aushadhi price substitution
- Daily voice check-in calls
- SMS
- Native iOS application
- Multi-tenant hospital deployment

## 8. Cut order under time pressure

If time runs short, remove features in this order:

1. WhatsApp escalation. Email is the fallback.
2. Arjun's adherence log.
3. Cognito and care-circle complexity. A single-device demo can continue.
4. Extra-strip detection in Box Check.

The Box Check feature itself must remain. The product loses its main differentiation if it becomes only a prescription reader.

## 9. Demo case

The primary demo is a post-cardiac-event discharge:

- Five to seven medicines
- Brand confusion between Ecosprin, Clopitab, Atorva, and similar names
- A genuine duplicate-molecule risk, such as two brands containing pantoprazole
- A combination medicine
- A PRN medicine
- Red flags where misunderstanding can cause severe harm

The case01 synthetic fixture contains:

- Ecosprin, aspirin 75 mg, morning, after food, 30 days
- Clopitab, clopidogrel 75 mg, night, after food, 30 days
- Atorva, atorvastatin 40 mg, bedtime, 30 days
- Pan, pantoprazole 40 mg, morning and night, before food, 14 days
- Pantocid, pantoprazole 40 mg, morning, before food, duration not stated
- Glycomet GP1, metformin 500 mg plus glimepiride 1 mg, morning and night, after food, 30 days
- Sorbitrate, isosorbide dinitrate 5 mg, SOS, for chest pain

The case deliberately includes duplicate pantoprazole exposure, a two-molecule combination, a PRN line, and missing duration.

## 10. User experience and screen order

The intended build order is:

1. Upload
2. Review and Confirm
3. Schedule
4. Box Check
5. Red flags
6. Fridge sheet
7. Arjun's view
8. Settings
9. Circle and Invite
10. Sign-in

The last two screens can initially be faked with a URL parameter while Cognito is being wired.

### Persistent shell

- Bottom navigation has Schedule, Box Check, and Red flags.
- There is no hamburger menu.
- The footer on every screen says: AfterCare re-displays what your doctor wrote. It never changes a dose.
- The app is designed for one-handed use and bright sunlight.
- Normal body text is at least 18 pixels.
- Primary buttons are at least 56 pixels tall and use at least 20 pixel text.
- Target contrast for normal text is 7:1.
- Green means given or matched.
- Amber means confirm or check.
- Red means missed or do not take.
- Color is never the only state signal. Every state has an icon and a written label.
- Kannada and Hindi fonts are self-hosted. The product uses Noto Sans Kannada and Noto Sans Devanagari.
- No hover-only interaction is acceptable.

### Upload screen

Required browser input:

~~~html
<input type="file" accept="image/*" capture="environment">
~~~

Behavior:

- Use the native camera picker. No camera library is required.
- Support multiple pages.
- Show thumbnails.
- Provide an add-another-page action.
- Drag reordering is out of scope.
- Show upload progress and per-page failure state.
- Keep extraction loading visible for up to 120 seconds.
- Never make the user think a long extraction request failed merely because it took longer than a normal API call.

### Review and Confirm screen

Show one medicine card per extracted line:

- Brand
- Molecule name or names
- Strength and unit
- Form
- Raw prescription text
- Frequency
- Resolved slots
- Food relation
- Duration
- PRN status and condition
- Confidence
- Confirmation state
- Source crop when available

Rules:

- Amber fields require a user tap before activation.
- A missing strength, frequency, or duration remains null.
- The client must not infer a value from another medicine, a common abbreviation, or a drug database.
- If the user edits strength or frequency, send userEdited true with the plan patch.
- Cosmetic edits such as a display name change do not count as a dose change, but the original source data must remain intact.
- The activation control is disabled while any medicine needs confirmation.

### Schedule screen

The main grid:

- Rows are medicines.
- Columns are morning, noon, night, and bedtime.
- Filled cells indicate scheduled use.
- Empty cells indicate no scheduled dose.
- Show the slot time in IST.
- Show a food icon or text for before food and after food.
- One Given action exists for the whole slot. It is not repeated for every medicine.
- Medicines sharing a slot are grouped under the same dose action.
- Pending, given, and missed states have icon plus text.
- A missed dose must not be described as a medical recommendation. The UI should direct the user to the configured product flow and ask the doctor when the product copy requires it.

PRN section:

- Label it Only when needed.
- Never place PRN medicines into the scheduled slot grid.
- Show the PRN condition exactly when available.
- PRN has no generated routine dose records.

Audio:

- The planned speaker action calls GET /plans/{planId}/audio.
- The audio route is missing from the current OpenAPI file and current main branch, so the frontend must use a typed mock until that contract is formalized.
- Kannada users are planned to hear Hindi audio because Polly does not provide the intended Kannada voice in Mumbai.

Offline:

- Cache the active schedule in the service worker.
- Queue Given actions.
- Use doseId as the idempotency key.
- Show an offline or queued state.
- Reconcile the queue when the connection returns.

### Box Check screen

Behavior:

1. Open the native camera input.
2. Capture one or more strip photos.
3. Upload the photos through the document upload flow.
4. Submit planId and strip documentId to POST /boxcheck.
5. Render every returned item.

Verdicts:

- matched: the molecule and strength match the prescription.
- check: the user should check with a chemist or doctor.
- do_not_take: the user should not take it until asking the doctor.

The API returns a message for each item. The client displays that message and does not invent alternative medical wording.

Reasons include:

- exact_match
- strength_mismatch
- combination_extra
- brand_unreadable
- missing_from_box
- not_prescribed
- duplicate_molecule
- combination_strip
- unreadable_strip
- strength_unreadable

The interface must never say safe to take.

### Red flags screen

- Render the API text verbatim.
- If source is document, state that the text came from the discharge summary.
- If source is generic, show a visible band reading General advice. Not from your document.
- Do not add warnings from client-side medical logic.
- If source crop support is returned, show it. The current contract does not define enough page information to reliably support multi-page red-flag crops.

### Fridge sheet

- Render the schedule grid to a canvas.
- Export a PNG.
- Trigger download.
- Offer the browser share sheet where available.
- Print readability matters more than color.
- Every status must remain distinguishable in black and white.
- Include medicine names, slot labels, food relationship, and the product safety disclaimer.

### Arjun's view

- Read-only schedule.
- Adherence history through GET /plans/{planId}/adherence.
- Given percentage when the endpoint returns it.
- Missed or pending history.
- No plan editing in the caregiver view.

### Settings and install help

- Include Delete my data within two taps.
- Explain PWA installation.
- Detect iOS Safari and show Add to Home Screen instructions before push permission.
- Request notification permission only after a user tap.
- Do not use analytics or third-party tracking.

## 11. Domain semantics

### Frequency parser

Frequency parsing is deterministic and never guesses unknown input.

Mappings:

- OD, QD, daily, once daily: morning
- BD, BID, twice daily: morning and night
- TDS and TID: morning, noon, and night
- QID and QDS: morning, noon, night, and bedtime
- HS, nocte, at bedtime: bedtime
- 1-0-1: morning and night
- 1-1-1: morning, noon, and night
- 0-0-1: night
- 1-1-1-1: all four slots
- SOS, PRN, as needed, if needed, when required: no scheduled slots and PRN true
- Empty, weekly, and alternate days: no slots and not PRN

Unknown frequency returns an empty slot list and false PRN. The system must not convert an unknown value into a guessed schedule.

### Slot times

Defaults per circle:

- Morning: 08:00 IST
- Noon: 14:00 IST
- Night: 20:00 IST
- Bedtime: 22:00 IST

The user may edit slot times per circle. Backend scheduling is stored or created in UTC after interpreting the times in Asia/Kolkata.

### Duration

- durationDays controls the plan's scheduled end.
- When durationDays is null, the backend schedules seven days by default.
- The UI labels the medication Duration not stated. Ask your doctor.

### Dose granularity

The system creates one dose record per slot per day, not one record per medicine. This allows one Given tap for every medicine in the 08:00 morning slot.

A slot becomes missed when no Given event arrives inside the circle escalation window after its reminder. The product specification says the default escalation window is 60 minutes. The current circle implementation writes 30 minutes by default, which is a known mismatch.

## 12. Safety model

Safety is enforced in backend code and tests. Prompt-only safety is not sufficient.

### No dose modification

The API rejects an edited plan when a molecule, strength, frequency, slots, PRN state, duration, unit, or related dose signature changes without userEdited true.

When userEdited is false:

- Medicine line IDs cannot be added, removed, or renamed.
- Molecule name, normalized strength, unit, frequency, slots, PRN, duration, source, and source block IDs must remain unchanged.
- Duplicate line IDs are always rejected.

### No invented red flags

- redFlags.source must be document or generic.
- A document red flag requires non-empty sourceBlockIds.
- A generic red flag must use the fixed constant exactly.

Fixed generic red flag:

~~~text
Call your doctor or 108 immediately for: chest pain, breathlessness, heavy bleeding, fever above 101°F, fainting or confusion. This is general advice — it was not found in your document.
~~~

### No filled-in gaps

- Missing strength, frequency, or duration remains null.
- A missing frequency with scheduled slots is invalid.
- A non-PRN medicine with null frequency must require confirmation.
- A medicine with confidence below 0.85 must require confirmation.
- A medicine using the vision-only fallback may have no source block IDs but must require confirmation.

### Activation gate

Activation is rejected when:

- Plan validation returns any error.
- Red flags are missing.
- Any medicine needs confirmation.
- The plan has no medicines.

### Box Check language

The product never says safe to take. Approved tiers are:

- Matches your prescription.
- Check with your chemist.
- Do not take. Ask your doctor.

### Persistent disclaimer

Every screen carries:

~~~text
AfterCare re-displays what your doctor wrote. It never changes a dose.
~~~

## 13. Extraction pipeline

The intended data path is:

~~~text
image or PDF
  -> private S3
  -> Textract AnalyzeDocument with TABLES and LAYOUT
  -> WORD blocks with IDs and normalized bounding boxes
  -> Bedrock Converse with the image and Textract word list
  -> strict structured plan JSON
  -> source block IDs and confidence
  -> union bounding-box crop
  -> client-side crop rendering from the original page
~~~

Textract behavior:

- Textract reads Latin scripts supported by the service.
- Printed Indian prescriptions are expected to be mostly English.
- If a page produces fewer than 20 WORD blocks, the fallback is Bedrock vision on the raw image.
- Fallback fields use source vision_only.
- Vision-only fields do not have reliable crops and require confirmation.

Bedrock behavior:

- Claude Sonnet 5 is the planned accuracy model for document extraction.
- The prompt requests strict JSON containing medicines, red_flags, and follow_up.
- Every extracted field should carry source block IDs and confidence from 0 to 1.
- A Bedrock Guardrail is planned for dosage advice, substitution advice, and diagnosis.
- Nova Lite is planned for low-risk verdict or summary phrasing.

Crop behavior:

- Textract block IDs are mapped to a union bounding box.
- The intended stored shape is documentId, page, x, y, w, h.
- Coordinates are normalized from 0 to 1.
- The frontend renders the crop from the original uploaded image.
- No separate crop object is intended in S3.

Known contract problem: the current OpenAPI crop schema includes only x, y, w, and h. It omits documentId and page. The frontend cannot reliably render a crop for a multi-page document until this is resolved.

## 14. Plan data model

### Molecule

Fields:

- name: required string
- strengthMg: number or null
- unit: mg, iu, or ml; default mg

Mass units are normalized to mg. IU and ml retain their own unit.

### Medicine

Fields:

- lineId: required stable line identifier
- rawText: original prescription line
- molecules: zero or more Molecule objects
- brand: string or null
- form: tablet, capsule, syrup, injection, drops, inhaler, ointment, or null
- frequency: verbatim notation such as OD, BD, TDS, HS, SOS, or 1-0-1; null if not stated
- slots: morning, noon, night, bedtime; empty for PRN
- foodRelation: before, after, or unspecified
- durationDays: integer or null
- prn: boolean
- prnCondition: string or null
- confidence: number from 0 to 1
- sourceBlockIds: Textract WORD IDs; can be empty only for vision_only
- source: textract or vision_only
- needsConfirmation: boolean
- crop: normalized crop object or null

### RedFlags

Fields:

- source: document or generic
- text: display text
- sourceBlockIds: required and non-empty when source is document

### Plan

Fields:

- planId
- circleId
- patientName: nullable
- sourceDocumentIds
- medicines
- redFlags
- followUp: nullable object containing date, with, and confidence
- slotTimes
- language: kn, hi, or en
- status: draft, active, or archived

### Dose

Fields:

- doseId
- date
- slot
- status: pending, given, or missed
- givenAt
- givenBy
- medicineLineIds

## 15. Box Check implementation semantics

The backend pure engine receives prescribed medicines and detected strips.

Strip data:

- brandText may be null
- molecules is a list of Molecule objects

Matching rules:

1. Normalize molecule names and units.
2. Compare composition before brand names.
3. Exact match requires equal molecule sets and known equal strengths.
4. A matching molecule with different strength is amber.
5. A matching molecule with unreadable strength is amber with strength_unreadable.
6. An unreadable brand with matching composition is amber with brand_unreadable.
7. A strip containing a prescribed molecule plus extra unprescribed molecules is amber.
8. A strip that combines two prescribed lines can be amber as combination_strip.
9. A missing prescribed medicine is red with missing_from_box.
10. An extra strip with no prescribed molecule is red with not_prescribed.
11. A duplicate molecule under another brand is red with duplicate_molecule.
12. An unreadable strip is amber with unreadable_strip.

Output behavior:

- Every prescribed line receives one primary item in plan order.
- Unconsumed strips are appended after primary line items.
- A line can receive additional items when duplicate or extra packs are discovered.
- A PRN line and regular line of the same drug are not automatically treated as duplicates when their PRN flags differ.

Drug normalization:

- Brand text removes leading T or C prefixes, dosage forms, strengths, pack descriptors, punctuation, and certain strip phrases.
- Brand lookup uses a four-character normalized prefix bucket.
- Candidate matching uses exact match first and difflib with a floor of 0.88.
- Composition parsing handles mg, mcg, g, ml, IU, combination plus signs, equivalent-to text, per-volume clauses, and common pharmacopoeia suffixes.
- A small synonym map covers amoxicillin/amoxycillin, acetaminophen/paracetamol, elemental iron/iron, and clavulanate variants.
- Ferrous salts are deliberately kept distinct.
- Unit mismatch does not match.
- Unknown drug brands return an empty result rather than throwing.
- DynamoDB lookup paginates through a bucket and returns an empty result when the query fails, avoiding a wrong partial match.

## 16. Authentication and care circles

### Cognito owner flow

- AWS Cognito User Pool uses email sign-in.
- The intended user experience is passwordless email OTP.
- The user pool is Essentials tier.
- Owner authentication produces a Cognito ID token.
- The backend verifies RS256 signature using the pool JWKS.
- The backend checks issuer, audience, expiration, token_use=id, and the token key ID.
- The owner must exist as an owner member in the target circle.

### Invite caregiver flow

- Owner calls POST /circles/{circleId}/invite.
- The backend creates a random token.
- The stored invite key is a SHA-256 hash of the token.
- The invite expires after 24 hours.
- The invite is single use.
- The returned URL uses the web origin and query parameters c and t.
- Caregiver calls POST /circles/{circleId}/join with the token.
- The backend atomically claims the invite, checks circle and expiration, creates a caregiver member, and returns a session token.
- The session token is HS256 signed with a secret in Secrets Manager.
- The token carries sub, circleId, role=caregiver, iss=aftercare, iat, and exp.
- The token lifetime is 90 days.
- A caregiver token is scoped to one circle.
- A caregiver cannot create a circle, edit a plan, activate a plan, or create an invite.
- A caregiver can read schedule information, mark doses given, and use Box Check.

### Current implemented auth routes

The current main branch includes:

- POST /circles
- POST /circles/{circleId}/invite
- POST /circles/{circleId}/join

The current route implementation uses Secrets Manager for the circle-token secret and caches Cognito JWKS for the Lambda container lifetime.

## 17. Notifications

Event behavior:

- Dose due: Web Push to Shanta.
- Slot missed after the escalation window: repeated Web Push to Shanta, WhatsApp plus SES email to Arjun.
- Plan activated: SES email summary to Arjun.

Delivery:

- Web Push uses pywebpush and VAPID keys stored in Secrets Manager.
- iOS 16.4 or later requires PWA installation to the Home Screen before Web Push works.
- Push permission must be triggered by a user tap.
- WhatsApp uses AWS End User Messaging Social in ap-south-1.
- Business-initiated WhatsApp messages outside the 24-hour window require a Meta-approved template.
- The WhatsApp number cannot already be registered in the WhatsApp app.
- SES is assumed to be in sandbox with verified recipients only and a 200-message daily limit.
- The fallback chain is WhatsApp, SES, then an in-app banner.
- A notification failure must not block dose marking.

## 18. Privacy and security

- Raw document images expire after 30 days through the S3 lifecycle rule.
- S3 is private, encrypted, and blocks public access.
- The intended storage region is ap-south-1.
- No document text, medicine names, email addresses, phone numbers, or raw patient data should enter CloudWatch logs.
- The redaction helper logs value shape and length instead of content.
- Bedrock input handling is described as not used for model training under AWS defaults and this is intended to be disclosed in the demo.
- Delete my data removes all DynamoDB items under the circle and the corresponding S3 prefix.
- The delete action should be reachable in two taps from Settings.
- The PWA has no analytics, ad technology, or third-party tracking scripts.
- All committed documents and test data are synthetic.
- Do not put tokens, credentials, private patient documents, or local environment files in the frontend branch.

## 19. AWS architecture

### Frontend

- Next.js 15
- TypeScript
- App Router
- Tailwind
- static export with output=export
- PWA service worker
- Amplify Hosting
- browser-side API calls

No server-side rendering, server actions, Next API routes, or edge runtime is planned.

### Function URL API

- One Python 3.12 Lambda.
- Function URL rather than API Gateway because extraction can take longer than API Gateway's 29-second integration limit.
- Lambda timeout is configured for 120 seconds in the current CDK.
- Current memory is 1024 MB.
- Function URL auth type is NONE because JWT verification happens in application code.
- CORS is configured in CDK.
- The API router resolves method and path patterns and returns JSON responses.

### Reminder Lambda

- A second Python 3.12 Lambda is intended for reminder and escalation phases.
- Current CDK points its handler to api.reminder.lambda_handler.
- api/reminder.py is absent on current main, so this is a known incomplete deployment dependency.

### S3 documents bucket

- Stores uploaded document pages and strip photos.
- Private.
- KMS-managed encryption.
- SSL required.
- Public access blocked.
- 30-day lifecycle expiration.
- Intended key shape: circles/<circleId>/<documentId>/p<page>.<extension>
- Current CDK CORS allows all origins. The specification says it should be restricted to the Amplify origin. This is a configuration mismatch that should be fixed before production use.

### DynamoDB aftercare table

- Single-table design.
- Partition key PK.
- Sort key SK.
- On-demand billing.
- TTL field expiresAt.
- Point-in-time recovery is off in the current design.
- Destructive removal policy is intended for the hackathon stack.

Key shapes:

- PK CIRCLE#<cid>, SK META: circle name, language, slot times, escalation minutes.
- PK CIRCLE#<cid>, SK MEMBER#<userId>: role, email, push subscription, WhatsApp number.
- PK CIRCLE#<cid>, SK PLAN#<planId>: full plan JSON.
- PK CIRCLE#<cid>, SK DOSE#<yyyy-mm-dd>#<slot>: dose state and medicine line IDs.
- PK CIRCLE#<cid>, SK DOC#<documentId>: S3 key, page count, uploader, Textract cache key.
- PK INVITE#<hashed-token>, SK META: invite metadata and expiry.

### DynamoDB aftercare-drugs table

- PK is the first four characters of normalized brand.
- SK is the full normalized brand.
- Attributes include brand, molecules, manufacturer, pack size, and discontinued.
- Lookup queries one prefix bucket and paginates.

### Bedrock

Current config values in the repository are:

- BEDROCK_MODEL_ID: global.anthropic.claude-sonnet-5
- BEDROCK_CHEAP_MODEL_ID: apac.amazon.nova-lite-v1:0

The plan says model IDs must be resolved with aws bedrock list-inference-profiles at build time. Do not trust a remembered model ID.

### Textract

Use AnalyzeDocument with TABLES and LAYOUT. The extraction logic needs WORD blocks, block IDs, and normalized bounding boxes.

### Translate

Amazon Translate handles deterministic translation of schedule or summary text when required.

### Polly

- Planned Hindi voice: Kajal.
- Engine: neural.
- Polly audio is cached in S3 using a hash of plan and spoken text.
- Kannada display can use Kannada text, while spoken audio falls back to Hindi because of the Mumbai voice availability constraint.

### EventBridge Scheduler

- One-time schedule per dose slot.
- Scheduler invokes the reminder Lambda.
- The API Lambda needs CreateSchedule, DeleteSchedule, and iam:PassRole permissions.

### Cognito

- Email sign-in.
- Self sign-up enabled in current CDK.
- Email OTP is configured through the Cognito Essentials and SES path.
- CDK outputs UserPoolId and UserPoolClientId.

### SES and WhatsApp

- SES sender identity is configured in infra/config.py.
- SES is expected to be sandboxed for the demo.
- WhatsApp uses End User Messaging Social.

## 20. Infrastructure configuration

Current environment names passed to the API Lambda include:

- TABLE_NAME
- DRUGS_TABLE_NAME
- DOCS_BUCKET
- BEDROCK_MODEL_ID
- BEDROCK_CHEAP_MODEL_ID
- USER_POOL_ID
- USER_POOL_CLIENT_ID
- CIRCLE_SECRET_ARN
- WEB_ORIGIN

Current important configuration facts:

- Region is ap-south-1.
- The AWS account ID and SES sender are hardcoded in infra/config.py. Treat those values as private operational configuration.
- WEB_ORIGIN is still a placeholder in the repository and must match the real Amplify deployment before invite links are generated.
- README records a deployed API URL. Verify GET /health before using it because the recorded endpoint may become stale.

Build and deploy:

~~~powershell
powershell -ExecutionPolicy Bypass -File infra/build.ps1
npx aws-cdk@2 deploy --require-approval never
curl "https://<function-url>/health"
~~~

The build script:

1. Removes build/api.
2. Installs Lambda dependencies into build/api for Python 3.12 and Linux.
3. Installs source-only pywebpush dependencies.
4. Copies api/ into build/api/.

## 21. API contract

The intended OpenAPI contract is docs/api/openapi.yaml. It is described as frozen and is the source of truth for frontend development. Prism should mock it on port 4010.

Global security:

- Most routes use Bearer JWT.
- Owner routes use Cognito ID tokens.
- Caregiver routes use circle session tokens.
- POST /circles/{circleId}/join explicitly disables bearer security.

Error object:

~~~json
{
  "code": "unauthorized | forbidden | not_found | validation_failed | extraction_failed | conflict | auth_unavailable",
  "message": "human readable text",
  "details": {}
}
~~~

### GET /health

- Security: none.
- Response: status 200.
- Body: ok boolean and optional commit string.

### POST /documents

- Security: bearer.
- Body:

~~~json
{
  "circleId": "ci_...",
  "pageCount": 2,
  "contentType": "image/jpeg"
}
~~~

- pageCount range: 1 to 10.
- contentType: image/jpeg, image/png, or application/pdf.
- Response: 201.

~~~json
{
  "documentId": "doc_...",
  "uploads": [
    {
      "page": 1,
      "uploadUrl": "https://presigned-s3-url",
      "key": "circles/ci_.../doc_.../p1.jpg"
    }
  ]
}
~~~

The prose spec has an older single uploadUrl shape. The OpenAPI uploads array is authoritative.

### POST /documents/{documentId}/extract

- Security: bearer.
- Body: circleId.
- Long-running request, up to 120 seconds.
- Concurrent duplicate extraction is not idempotent-safe.
- Response: 200 Plan.
- 422 means extraction produced no usable result.

### GET /plans/{planId}

- Security: bearer.
- Response: Plan.
- 404 means the plan is unavailable.

### PATCH /plans/{planId}

- Security: bearer, owner only.
- Required body fields: medicines and userEdited.
- Optional fields: language and slotTimes.
- Response: updated Plan.
- 403 means role is not allowed.
- 422 means safety validation failed.

Example:

~~~json
{
  "userEdited": true,
  "medicines": [],
  "language": "kn",
  "slotTimes": {
    "morning": "08:00",
    "noon": "14:00",
    "night": "20:00",
    "bedtime": "22:00"
  }
}
~~~

### POST /plans/{planId}/activate

- Security: bearer, owner only.
- Response: active plan status, count of created doses, and firstDoseAt.
- 403 means role not allowed.
- 422 means confirmation or validation remains.

### POST /doses/{doseId}/given

- Security: bearer.
- Marks the shared slot as given.
- Response: Dose.
- 404 means the dose is unavailable.

### GET /plans/{planId}/adherence

- Security: bearer.
- Optional days query parameter, default 7, maximum 30.
- Response:

~~~json
{
  "doses": [],
  "givenPct": 0
}
~~~

### POST /boxcheck

- Security: bearer.
- Body:

~~~json
{
  "planId": "pl_...",
  "documentId": "doc_..."
}
~~~

- The document ID refers to an uploaded strip-photo document.
- Response contains items, each a BoxCheckItem.

### POST /circles

- Security: Cognito owner token.
- Body is optional.
- name defaults to Family and has a maximum length of 100.
- language is en, hi, or kn and defaults to kn.
- Response 201 with circleId.

### POST /circles/{circleId}/invite

- Security: bearer, owner only.
- Response 201 with token, url, and expiresAt.
- One prose section mentions qrPayload. The current implementation and OpenAPI use url. Frontend can turn the URL into a QR code.

### POST /circles/{circleId}/join

- Security: none.
- Body: token.
- Response 200 with sessionToken, role=caregiver, and circleId.
- 404 means invite is invalid, expired, already used, or scoped to another circle.
- 422 means token is missing or body is not a JSON object.

### POST /circles/{circleId}/push

- Security: bearer.
- Body contains the browser PushSubscription JSON:

~~~json
{
  "subscription": {
    "endpoint": "https://push-endpoint",
    "keys": {
      "p256dh": "base64",
      "auth": "base64"
    }
  }
}
~~~

- Response: 204.

### Planned audio route

The implementation plan describes GET /plans/{planId}/audio with lang and circleId query parameters. The planned response contains url, spokenLanguage, and text. This route is absent from the current OpenAPI file and current main branch, so it must be treated as a pending contract decision.

## 22. Current repository implementation

Current branch at audit time:

- Branch: main
- HEAD: 2b166f5, merge of Task 16 Cognito owner auth and invite-link caregiver sessions
- Working tree before adding context files: clean
- Python tests: 205 passed
- Frontend application: absent; web/ contains only AGENTS.md and handoff instructions

Current API modules present:

- api/auth.py
- api/boxcheck.py
- api/circles.py
- api/common.py
- api/drugs.py
- api/drugs_repo.py
- api/frequency.py
- api/handler.py
- api/models.py
- api/validate.py

Current infrastructure modules present:

- infra/aftercare_stack.py
- infra/app.py
- infra/build.ps1
- infra/config.py

Current data modules:

- data/etl_drugs.py
- data/make_docs.py
- ten fixture JSON files
- ten golden JSON files

Current API routes actually registered by api/handler.py:

- GET /health
- POST /circles
- POST /circles/{circleId}/invite
- POST /circles/{circleId}/join

The handler imports api.circles at module load. It does not currently import future document, plan, dose, Box Check API, speech, reminder, or notification modules.

Planned files absent from current main include:

- api/extract.py
- api/documents.py
- api/plans.py
- api/doses.py
- api/schedules.py
- api/reminder.py
- api/notify.py
- api/speech.py
- api/boxcheck_api.py
- api/seed.py
- scripts/seed_demo.py
- tests for documents, extraction, doses, reminders, speech, and live API flows

The CDK currently references api.reminder.lambda_handler for the reminder Lambda, so deployment completeness depends on that missing module.

## 23. Current pure logic behavior

Implemented and tested pure logic:

- Models and DynamoDB round-trip coercion
- Frequency parsing
- Plan validation
- Plan edit validation
- Brand normalization
- Molecule normalization
- Composition parsing
- Brand bucket lookup behavior
- Box Check matching and safety copy
- Synthetic document generation and golden JSON shape
- Auth token and circle behavior

The repository test suite covers edge cases such as:

- Unknown frequency never becomes a guessed schedule.
- PRN medicines must not have scheduled slots.
- Null frequency requires confirmation.
- Low confidence requires confirmation.
- Duplicate line IDs are rejected.
- Changing dose-related fields without userEdited is rejected.
- Adding or removing medicine lines without userEdited is rejected.
- Generic red flags must use the fixed constant.
- Document red flags need source blocks.
- Vision-only medicines can lack blocks but must be confirmed.
- Two brands with the same molecule and strength can match.
- Strength mismatch is amber.
- Missing medicine is red.
- Extra strip is red.
- Duplicate molecule is red.
- Unreadable strip is amber.
- The Box Check engine never emits safe language.
- Drug lookup paginates DynamoDB and returns empty on query failure.
- HTML fixture rendering escapes text fields.

## 24. Synthetic test corpus

The repository contains ten synthetic cases generated from a blank NABH E-Mitra-style discharge template. They are designed to vary layout, medicine complexity, missing fields, PRN behavior, and page breaks.

Corpus summary:

- case01: table layout, 7 medicines, 1 PRN, 1 combination, 2 missing durations
- case02: freetext layout, 4 medicines, 1 PRN, 3 combinations, 1 missing duration
- case03: table layout, 6 medicines, no PRN or combinations, complete values
- case04: table layout, 4 medicines, 2 PRN, 1 combination, 2 missing durations
- case05: table layout, 5 medicines, 1 combination, additional local-language hospital header
- case06: table layout, 6 medicines, 1 PRN, 2 combinations, 1 missing duration
- case07: OPD prescription-pad layout, 4 medicines, 1 PRN, 1 combination, 1 missing duration
- case08: table layout, 9 medicines, 1 PRN, 1 combination, page break after five medicine rows, 1 missing duration
- case09: table layout, 4 medicines, 1 PRN, 1 missing duration
- case10: table layout, 5 medicines, 1 PRN, 1 unknown strength, 2 missing durations

data/make_docs.py:

- Reads data/fixtures/*.json.
- Writes printable HTML under data/out/.
- Writes expected extraction JSON under data/golden/.
- Supports table, freetext, and opd layouts.
- Supports hospitalLocal, doctor, pageBreakAfter, and visitDate fixture fields.
- Escapes user-like text fields.
- Uses the deterministic frequency parser to derive expected slots and PRN values.

No real patient data should be added.

## 25. Quality gate

The intended golden extraction gate evaluates:

- Drug name: at least 90 percent
- Strength: at least 90 percent
- Frequency to slots: at least 80 percent
- Food relation: at least 80 percent
- Duration: at least 80 percent

The golden gate needs AWS credentials and uploaded photos:

~~~powershell
GOLDEN_S3_PREFIX=circles/ci_demo/golden python -m pytest -m golden -v -s
~~~

The plan also specifies a Sonnet 5 versus Nova Pro bake-off. If Nova Pro is within five points on every field, the plan is to switch extraction to the APAC Nova Pro profile to improve the residency story.

## 26. Cost assumptions

The project estimates:

- Textract: about 0.015 USD per page
- 100 test pages: about 1.50 USD
- Bedrock Sonnet 5: about 0.02 USD per document extraction
- Lambda, DynamoDB on-demand, S3, and Scheduler: pennies at demo scale
- Cognito Essentials: free below 10,000 monthly active users
- Amplify Hosting: free tier
- Hackathon total: well under 20 USD of the 200 USD credit
- AWS Budgets alarm: 50 USD
- Fixed monthly cost at zero users: expected to be 0 USD because no provisioned capacity is used

These are planning estimates from the repository and should be rechecked before a public launch.

## 27. Risks and mitigations

Live extraction may fail during recording:

- Seed a demo circle with the same downstream data path.
- Record the risky live scan once.
- Use the seeded state for stable downstream demonstrations.

Meta may reject WhatsApp:

- Submit the approved template early.
- Keep SES as the fallback.

Textract may miss page layout:

- Fall back to Bedrock vision.
- Mark fields vision_only.
- Force confirmation.

The drug dataset is from 2022:

- Give printed composition priority.
- Treat brand data as convenience data, not the source of truth.

Amplify may be incompatible with Next.js 16:

- Pin Next.js 15.

The frontend may be blocked by backend progress:

- Freeze the OpenAPI contract.
- Start Prism mock work immediately.

Bedrock model IDs may be wrong:

- Resolve them with the AWS CLI at build time.

Time may expire:

- Hard freeze is September 20, 2026 at 14:00 IST.
- Finish video and writeup after the product flow freezes.

## 28. Hackathon judging story

Idea and impact:

- Indian clinical evidence.
- A caregiver-centered product.
- Vernacular and pictorial access.

Built on AWS:

- Amplify
- Lambda
- Lambda Function URL
- S3
- DynamoDB
- Textract
- Bedrock
- Translate
- Polly
- EventBridge Scheduler
- Cognito
- SES
- AWS End User Messaging Social

Learning:

- First Bedrock Guardrail
- First EventBridge Scheduler usage
- First CDK stack
- First End User Messaging Social usage

Execution:

- One visible flow: paper, schedule, box, escalation.

Demo assets:

- Printed discharge summary
- Pill box
- Medicine strips
- Two phones

The strongest product line:

Everyone reads the prescription. We check that the paper matches the pill box.

## 29. Frontend engineering rules

The frontend owner or frontend AI agent must:

- Read this file, docs/frontend-handoff.md, docs/spec.md, docs/api/openapi.yaml, and README.md before coding.
- Build under web/.
- Use Next.js 15, TypeScript, App Router, Tailwind, and static export.
- Use NEXT_PUBLIC_API_BASE.
- Use a typed API client.
- Use Prism on port 4010 while routes are missing.
- Keep auth behind a session adapter.
- Preserve null and needsConfirmation.
- Never infer a medicine value.
- Send userEdited true when strength or frequency changes.
- Keep activation disabled while confirmation remains.
- Use API-provided Box Check messages.
- Never say safe to take.
- Render red flags verbatim.
- Preserve the disclaimer on every screen.
- Self-host Kannada and Devanagari fonts.
- Test offline queueing and idempotency by doseId.
- Ask for push permission only from a user gesture.
- Avoid secrets, PII, analytics, tracking scripts, and raw document logging.
- Run npm run lint, npm run build, and npx tsc --noEmit before reporting completion.

## 30. Frontend and backend contract gaps

These gaps must be treated as explicit engineering decisions:

1. Audio route:
   The implementation plan describes GET /plans/{planId}/audio, but OpenAPI and current main do not define it.

2. Medicine crop page:
   The product spec expects documentId and page. OpenAPI defines only x, y, w, and h.

3. Red-flag crop:
   The frontend task requests a red-flag crop, but RedFlags has no crop or page field in OpenAPI.

4. Invite QR shape:
   One plan section says qrPayload. Current API code and OpenAPI return url. Use url until the contract changes.

5. Document upload response:
   Prose says uploadUrl. OpenAPI says uploads array. Use uploads array.

6. Escalation default:
   Spec says 60 minutes. Current api/circles.py writes 30 minutes.

7. S3 upload CORS:
   Spec intends the Amplify origin only. Current CDK allows all origins.

8. Reminder Lambda:
   CDK references api.reminder.lambda_handler. The module is missing from current main.

9. Demo seed:
   The plan references scripts/seed_demo.py and a seeded ci_demo circle. Those files are absent from current main.

10. Current live deployment:
    README records an API URL, but its current health and route coverage must be checked before relying on it.

## 31. Sharing checklist

Give the frontend owner:

- The full repository.
- docs/aftercare-complete-product-context.md.
- docs/frontend-handoff.md.
- web/AGENTS.md.
- docs/api/openapi.yaml.
- docs/spec.md.
- README.md.
- data/fixtures and data/golden.
- The current main commit or a branch made from it.

Do not share:

- .venv
- build artifacts
- cdk.out
- node_modules
- .env files
- raw patient material
- AWS credentials
- private agent settings

Before handing over:

1. Commit the two frontend handoff files and this product context file.
2. Tell the teammate that most API routes are currently mocked.
3. Tell the teammate that OpenAPI is the intended contract.
4. Tell the teammate which contract gaps require backend coordination.
5. Give the teammate the Prism startup command.
6. Keep frontend and backend branches separate.

## 32. Source map

Product and UX:

- README.md
- docs/spec.md
- docs/frontend-handoff.md
- docs/superpowers/plans/2026-09-18-aftercare.md

API:

- docs/api/openapi.yaml
- api/handler.py
- api/auth.py
- api/circles.py
- api/models.py

Pure domain logic:

- api/frequency.py
- api/validate.py
- api/drugs.py
- api/boxcheck.py
- api/drugs_repo.py

Infrastructure:

- infra/aftercare_stack.py
- infra/app.py
- infra/config.py
- infra/build.ps1

Synthetic data:

- data/fixtures/*.json
- data/golden/*.json
- data/make_docs.py
- data/etl_drugs.py

Tests:

- tests/test_auth.py
- tests/test_boxcheck.py
- tests/test_drugs.py
- tests/test_drugs_repo.py
- tests/test_frequency.py
- tests/test_handler.py
- tests/test_make_docs.py
- tests/test_models.py
- tests/test_validate.py

The repository has a strong pure-logic foundation and a frozen intended contract. The frontend can start immediately against Prism. Live integration depends on completing and merging the missing backend modules and resolving the listed contract gaps.
