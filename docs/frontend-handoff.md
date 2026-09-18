# AfterCare frontend handoff

This document is the working brief for the frontend owner and frontend coding agents.

## Verified repository state

Checked on September 18, 2026:

- The repository is on main with a clean working tree.
- web/ contains only the frontend agent instructions. No Next.js frontend has been committed yet.
- The intended frontend is Next.js 15, TypeScript, App Router, Tailwind, and static export.
- The backend test suite passes with 205 passed using .venv/Scripts/python.exe -m pytest -q.
- The current main Lambda router registers only these routes:
  - GET /health
  - POST /circles
  - POST /circles/{circleId}/invite
  - POST /circles/{circleId}/join
- The document, extraction, plan, dose, Box Check, push, and audio routes described in the product contract are not present on main yet.

The frontend must therefore be built against the Prism mock first. A live backend integration should happen only as each route is merged and deployed.

## Files to give the frontend owner

Give the teammate the repository, including these files as the primary context:

- README.md for the product summary, stack, deployment region, and recorded API URL.
- docs/spec.md for product behavior, safety rules, screen order, privacy requirements, and design constraints.
- docs/api/openapi.yaml for request and response types. This is the frontend/backend contract.
- docs/superpowers/plans/2026-09-18-aftercare.md for the frontend work breakdown in section Frontend tasks (teammate, against the Prism mock).
- data/fixtures/case01.json through data/fixtures/case10.json for synthetic discharge-summary inputs.
- data/golden/case01.json through data/golden/case10.json for expected structured extraction output.
- api/models.py for the Python representation of plans, medicines, molecules, and doses.
- api/auth.py for owner versus caregiver token behavior.
- api/circles.py for the implemented invite-link flow and query parameter names.
- api/handler.py for current route registration and response shape.
- api/validate.py, api/frequency.py, and api/boxcheck.py for safety rules, schedule semantics, and verdict meanings.
- infra/aftercare_stack.py and infra/config.py only when wiring deployed Cognito and API values. The frontend should not modify these files as part of normal UI work.

The backend test files are useful when a response behavior is unclear. They are not required for ordinary UI work.

Do not copy generated or machine-specific material into the frontend branch:

- .venv/
- build/
- cdk.out/
- __pycache__/
- .pytest_cache/
- aftercare.egg-info/
- node_modules/
- .env* files
- raw or private document folders such as data/photos/ and data/drugs_raw/
- personal agent configuration under .claude/ unless a specific instruction is needed

The committed fixtures are synthetic. They contain no real patient data.

## Branch and ownership workflow

Use a separate branch from the current main commit:

~~~powershell
git switch main
git pull --ff-only
git switch -c frontend/<teammate-name>
~~~

The frontend owner should normally modify only web/ and, when required, frontend documentation. Backend, infrastructure, data, and API contract changes stay with the backend owner unless both owners agree.

Commit small working slices such as shell, upload, review, schedule, Box Check, and PWA behavior. Do not rewrite backend files to make the Prism mock or a UI test pass.

## Local frontend setup

Run these commands from the repository root:

~~~powershell
Move-Item web/AGENTS.md web/AGENTS.md.handoff
npx create-next-app@15 web --typescript --tailwind --app --no-src-dir --use-npm
Move-Item web/AGENTS.md.handoff web/AGENTS.md
cd web
npm install
~~~

The temporary move lets create-next-app see an empty directory. Restore AGENTS.md immediately after scaffolding. If scaffolding fails, move web/AGENTS.md.handoff back to web/AGENTS.md before retrying.

Start the contract mock in a second terminal from the repository root:

~~~powershell
npx @stoplight/prism-cli mock docs/api/openapi.yaml -p 4010
~~~

Run the frontend against the mock:

~~~powershell
cd web
$env:NEXT_PUBLIC_API_BASE = "http://127.0.0.1:4010"
npm run dev
~~~

The application must read the API base URL from NEXT_PUBLIC_API_BASE. Do not hardcode the deployed URL in components. Static export means this value is supplied at build time.

The current README records this deployed Function URL:

~~~text
https://ctj5ower7vmwubklgwntkqdwsi0aemrx.lambda-url.ap-south-1.on.aws/
~~~

Verify GET /health before using it for integration because deployment state can change.

## Required Next.js constraints

Configure the frontend for static export:

~~~js
const nextConfig = {
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
~~~

Use client-side data fetching. Do not use SSR, server actions, API routes, or an edge runtime. Amplify serves the exported static files and the browser calls the Lambda Function URL directly.

Keep API access in one typed client such as web/lib/api/client.ts. UI components should not build endpoint strings or parse raw response errors independently.

## Contract rules the frontend must implement

### Authentication

- The bearer header is Authorization: Bearer <token>.
- An owner uses a Cognito ID token.
- A caregiver receives an AfterCare session token from POST /circles/{circleId}/join.
- The join endpoint is intentionally unauthenticated and accepts { "token": "..." }.
- Invite links use the query parameters c for circleId and t for the invite token. This matches api/circles.py.
- Keep token lookup behind an auth/session adapter. Do not scatter Cognito or caregiver-token logic across pages.
- A caregiver can view the schedule, mark a dose as given, and run Box Check. A caregiver cannot edit or activate a plan.

### Upload and extraction

The intended flow is:

1. Collect one or more pages with the native file input.
2. Call POST /documents with circleId, pageCount, and contentType.
3. Upload each file with PUT to the matching item in the returned uploads array.
4. Call POST /documents/{documentId}/extract with circleId.
5. Keep a visible progress state for up to 120 seconds.
6. Render the returned draft plan in Review and Confirm.

The OpenAPI response is { documentId, uploads[] }. Each upload item contains page, uploadUrl, and key. The older prose in docs/spec.md says { documentId, uploadUrl }; follow the OpenAPI file.

Use the exact file Content-Type when performing a presigned PUT. Keep a batch's page types consistent with the contentType sent to POST /documents.

### Plan and medicine display

The important plan fields are:

- planId, circleId, patientName, sourceDocumentIds, status
- medicines[]
- redFlags
- followUp
- slotTimes
- language

Each medicine may contain multiple molecules. Render the brand, molecule names, strength plus unit, form, raw text, frequency, slots, food relation, duration, and PRN condition when present.

Treat null as an unknown value. Do not fill it with an inferred value. A medicine with needsConfirmation: true remains unresolved until the user confirms or edits it.

When the user changes strength or frequency, send userEdited: true in the plan patch. The client must never silently alter a dose or frequency.

### Schedule

- Render rows by medicine and columns in this order: morning, noon, night, bedtime.
- A filled slot means the medicine is scheduled. An empty slot means it is not scheduled.
- Show one Given action per dose slot, not one action per medicine.
- A dose record is identified by doseId and has pending, given, or missed status.
- Group medicines sharing a slot under the same dose action.
- Put PRN medicines in a separate Only when needed section. PRN medicines have empty slots and may have prnCondition.
- The default IST slot times are morning 08:00, noon 14:00, night 20:00, and bedtime 22:00.
- If durationDays is absent, show Duration not stated. Ask your doctor.

The main schedule uses POST /doses/{doseId}/given. A successful response is a Dose object. For offline use, queue the action and reconcile the server response later. The queue must be idempotent by doseId.

### Box Check

The intended flow is:

1. Photograph medicine strips with the native camera input.
2. Upload the strip photos through the document upload flow.
3. Call POST /boxcheck with planId and the strip-photo documentId.
4. Render every item returned in items.

Use the API-provided message. Do not invent or soften verdict copy.

- matched means the strip matches the prescription.
- check means the user must check with a chemist or doctor.
- do_not_take means the user must not take it until asking the doctor.

The UI must never say that a strip is safe to take.

### Red flags

- Render redFlags.text verbatim.
- When redFlags.source is document, label it as coming from the document.
- When redFlags.source is generic, visibly show General advice. Not from your document.
- Never add a client-generated warning.

## Known contract gaps to resolve before live integration

These are evidence-based gaps between the current files. Keep them visible in the branch and ask the backend owner before depending on them:

1. The product plan references GET /plans/{planId}/audio, but docs/api/openapi.yaml does not define that route and main does not register it.
2. The product spec says a source crop includes documentId and page, but the OpenAPI Medicine.crop schema currently contains only normalized x, y, w, and h. Multi-page crop rendering cannot be reliable without a page or document association.
3. The W6 task asks for a red-flag source crop, but the OpenAPI RedFlags schema has no crop or page field.
4. The implementation plan mentions qrPayload for invites in one place. The current API returns url, token, and expiresAt. Use url and generate a QR code in the client only if the UI needs one.
5. The plan references seeded demo files such as scripts/seed_demo.py, but those files are not present on main. Do not assume a seeded live demo exists.

Until these are resolved, the frontend can use a local adapter or fixture data for the affected screens. Do not silently invent a backend response shape.

## UI and safety requirements

- Body text is at least 18px.
- Primary actions are at least 56px tall and use 20px or larger text.
- Use high contrast suitable for bright sunlight. Target a 7:1 contrast ratio for normal text.
- Use a bottom bar with Schedule, Box Check, and Red flags. Do not add a hamburger menu.
- Self-host Noto Sans Kannada and Noto Sans Devanagari. Do not depend on a CDN font.
- Every state has an icon and a word. Color alone cannot communicate given, check, missed, matched, or do-not-take.
- Every screen carries this exact disclaimer: AfterCare re-displays what your doctor wrote. It never changes a dose.
- No analytics, ad technology, or third-party tracking scripts.
- Ask for notification permission only after a user tap.
- On iOS Safari, explain Add to Home Screen before requesting push permission.
- Preserve patient privacy in browser logs. Do not log document contents, medicine names, tokens, or email addresses.

## Suggested frontend structure

The exact structure is the frontend owner's decision. A maintainable starting point is:

~~~text
web/
  app/
    page.tsx                 upload and entry
    review/page.tsx          review and confirm
    schedule/page.tsx        active schedule
    box-check/page.tsx       strip matching
    red-flags/page.tsx       warnings and source label
    fridge-sheet/page.tsx    printable/shareable PNG
    adherence/page.tsx       read-only Arjun view
    join/page.tsx            caregiver invite exchange
    settings/page.tsx        privacy and install help
    layout.tsx
    manifest.ts
  components/
  lib/
    api/client.ts
    api/types.ts
    auth/session.ts
    demo/fixtures.ts
    offline/queue.ts
  public/
    fonts/
    icons/
    sw.js
  next.config.js
  package.json
  README.md
~~~

Keep route pages thin. Put request construction, response parsing, session handling, offline queueing, and fixture selection in lib/.

## Definition of done for the frontend branch

- The frontend starts locally against the Prism mock.
- npm run lint passes.
- npm run build produces a static export.
- The upload, review, schedule, Box Check, red-flag, and fridge-sheet flows have usable loading, empty, success, and error states.
- The schedule does not activate while unresolved confirmation fields remain.
- Dose actions are grouped by slot and are safe to retry.
- All verdict and safety copy comes from the contract or the fixed product copy.
- The branch documents any backend dependency that is still mocked.
- The deployed build is tested against GET /health and each backend route that has actually been merged.
