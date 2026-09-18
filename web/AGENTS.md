# Frontend agent instructions

## Read first

Before changing code, read:

1. ../docs/frontend-handoff.md
2. ../docs/spec.md
3. ../docs/api/openapi.yaml
4. ../README.md

The repository root instructions also apply.

## Scope

The frontend lives in web/. Keep ordinary frontend changes inside this directory. Do not modify api/, infra/, data/, or the OpenAPI contract to make a UI task easier. If the contract is missing a field or route, record the gap and coordinate with the backend owner.

Do not add secrets, real patient information, tokens, email addresses, or AWS credentials to the repository.

## Architecture rules

- Use Next.js 15 with TypeScript, App Router, Tailwind, and output: export.
- Fetch data from the browser. Do not add SSR, server actions, API routes, or edge runtime code.
- Read the API base URL from NEXT_PUBLIC_API_BASE.
- Route all HTTP calls through one typed API client.
- Keep Cognito owner sessions and caregiver invite sessions behind an auth/session adapter.
- Use the Prism mock from ../docs/api/openapi.yaml while backend routes are missing or undeployed.
- Keep mock fixtures behind an explicit demo or mock adapter. Do not make fixture data look like a live API response without labeling the mode in development code.

## Safety rules

- Display extracted values. Do not infer missing strength, frequency, duration, food relation, warning text, or diagnosis.
- Preserve null values and needsConfirmation.
- Any strength or frequency edit must cause the plan patch to include userEdited: true.
- Do not enable plan activation while unresolved confirmation fields remain.
- Use API-provided Box Check messages. Never use safe to take language.
- Render red flags verbatim and distinguish document from generic.
- Keep the exact disclaimer on every screen: AfterCare re-displays what your doctor wrote. It never changes a dose.

## Interaction rules

- Use native file input with accept=image/* capture=environment for camera capture.
- Treat extraction as a long-running request that can take up to 120 seconds.
- Upload every returned presigned URL with the matching file content type.
- Make dose Given actions idempotent by doseId.
- Persist an offline queue for pending Given actions and show when a queued action has not synced.
- Do not request push permission without a direct user gesture.
- Use one bottom navigation bar with Schedule, Box Check, and Red flags.
- Do not use a hamburger menu.

## Accessibility and visual rules

- Body text is at least 18px.
- Primary buttons are at least 56px high with text at least 20px.
- Use high contrast suitable for bright sunlight.
- Every semantic state has an icon and a text label. Never rely on color alone.
- Self-host Noto Sans Kannada and Noto Sans Devanagari.
- All controls need keyboard focus, a visible focus style, and an accessible name.
- Error messages must identify the action that failed and the next safe action.

## API error handling

The API returns JSON errors with code, message, and optional details. Handle these codes explicitly where relevant:

- unauthorized: send the user to sign-in or invite joining.
- forbidden: explain that the current role cannot perform the action.
- not_found: explain that the plan, dose, document, or invite is unavailable.
- validation_failed: show the returned validation message without inventing a medical correction.
- extraction_failed: ask the user to retry or ask the doctor.
- conflict: refresh the resource before retrying.
- auth_unavailable: explain that sign-in verification is temporarily unavailable.

Do not log bearer tokens, invite tokens, document contents, medicine names, or patient names.

## Contract gaps

Do not assume these are available:

- GET /plans/{planId}/audio is referenced by the plan but absent from OpenAPI and current main.
- Medicine.crop lacks the page/document association required for reliable multi-page rendering.
- RedFlags lacks a crop/page field even though the UI task requests a source crop.
- The current main backend does not yet register document, extraction, plan, dose, Box Check, or push routes.

Use a typed mock adapter for these cases and leave a short note in the handoff document when the implementation depends on one.

## Verification before reporting completion

Run from web/:

~~~powershell
npm run lint
npm run build
npx tsc --noEmit
~~~

Also verify manually against the Prism mock:

- Upload state and long extraction loading state.
- Review state with a low-confidence medicine.
- Activation blocked until confirmation is complete.
- Grouped dose action for a shared slot.
- PRN medicine in the only-when-needed section.
- Matched, check, and do-not-take Box Check states.
- Document versus generic red-flag labeling.
- Offline queued Given action.
- Caregiver invite parsing from ?c=<circleId>&t=<token>.

Report the exact commands run and any route still served by a mock.
