# AfterCare frontend

Photograph an Indian hospital discharge summary. Get a picture-and-voice medicine
schedule. Then photograph the strips you bought and check that the pill box
matches the paper.

This app lives in `web/`. It is a **Next.js 15 static-export PWA**: the browser
talks to the API (or a local demo store). There is no SSR, no Next.js API
routes, and no server actions.

> AfterCare re-displays what your doctor wrote. It never changes a dose.

## Stack

- Next.js 15 (App Router) + React 19 + TypeScript
- Tailwind CSS v4
- `output: "export"` with `trailingSlash: true` and unoptimized images
- Client-side demo store (`localStorage`) until live document routes land
- Typed API client in `lib/api/client.ts` for the OpenAPI contract

## Run

From this directory:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

| Script | What it does |
| --- | --- |
| `npm run dev` | Turbopack dev server |
| `npm run build` | Static export to `out/` |
| `npm run lint` | ESLint |
| `npm run typecheck` | `tsc --noEmit` |

The landing page is marketing. **Get started** / **Photograph the paper** opens
the product flow. Upload any pages (or none) and run extraction — the demo
adapter loads the Hubli cardiac fixture and walks the screens.

Demo state is stored in the browser as `aftercare-demo-v1`. Reset it from
[Settings](/settings/).

## Routes

| Path | Screen |
| --- | --- |
| `/` | Marketing landing |
| `/upload/` | Photograph the discharge summary |
| `/review/` | Confirm extracted medicines (amber lines stay blocked) |
| `/schedule/` | Today’s slots: morning, noon, night, bedtime + Given |
| `/box-check/` | Photograph strips vs the active plan |
| `/red-flags/` | Document warnings, labelled separately from generic advice |
| `/fridge-sheet/` | Printable schedule |
| `/join/?c=&t=` | Caregiver invite (`c` = circle id, `t` = token) |
| `/settings/` | Privacy and delete data on this device |

Primary nav: Upload, Review, Schedule, Box Check, Red flags.

## Demo vs API

By default the UI is **demo-only**. Pages read `lib/demo/store.tsx`, which
hydrates a cardiac plan from `lib/demo/fixtures.ts`.

To point at a contract mock (when those routes exist):

```bash
# from the repository root
npx @stoplight/prism-cli mock ../docs/api/openapi.yaml -p 4010

# from web/
NEXT_PUBLIC_API_BASE=http://127.0.0.1:4010 NEXT_PUBLIC_USE_API=true npm run dev
```

- `NEXT_PUBLIC_API_BASE` is the Function URL or Prism origin. Do not hardcode it
  in components. Static export bakes this in at **build** time.
- `NEXT_PUBLIC_USE_API=true` flips `isDemoOnly()` in `lib/api/client.ts`.
- Live calls should wait until each route is actually registered on the backend.
  Today the deployed Lambda still only exposes circle + health endpoints.

Bearer tokens go in `Authorization: Bearer <token>`, via `lib/auth/session.ts`.

## Layout

```
web/
  app/                    routes, fonts, globals.css
  components/             shell, buttons, marketing landing
  lib/
    api/                  typed client + OpenAPI shapes
    auth/                 owner / caregiver session
    demo/                 fixture plan + client store
    copy.ts               disclaimer and nav labels
    format.ts             brand / frequency / food display
  public/                 illustrations, photos, PWA manifest
```

Keep route pages thin. Request construction, session, and fixtures stay in `lib/`.

## Design

Cream paper, ink type, blue actions.

| Token | Value |
| --- | --- |
| Cream / background | `#f4ede5` |
| Ink | `#212833` |
| Action blue | `#0061fe` |
| Story rail | `#000` |
| Card | `#ffffff` |

Display type is Satish; UI type is Funnel Display; the wordmark is Carmen Sans.
Kannada and Devanagari use Noto. Body copy is 18px or larger; primary buttons
are 56px tall with 20px type.

The landing hero uses a 16:9 photo (`public/photos/hero-care.png`), a phone
mockup with overlay cards, and an SVG marker scribble under the headline. The
“How AfterCare works” column is a sticky full-height stepper.

## Safety copy (do not invent)

- Never change a dose, never suggest a substitute, never fill a blank.
- Unreadable lines stay **ask doctor**.
- Box Check verdicts come from the contract: `matched`, `check`, `do_not_take`.
  Never say a strip is “safe to take”.
- Red-flag text from the document is verbatim. Generic advice is labelled
  **General advice. Not from your document.**
- Every screen carries: *AfterCare re-displays what your doctor wrote. It never
  changes a dose.*
- Status always has an icon **and** a word. Color alone is not enough.
- No analytics, ads, or third-party tracking.

## Related docs

Product spec, API contract, and backend live one level up:

- [Product README](../README.md)
- [Spec](../docs/spec.md)
- [OpenAPI](../docs/api/openapi.yaml)
- [Frontend handoff](../docs/frontend-handoff.md)
