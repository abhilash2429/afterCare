# AfterCare handoff, 2026-09-20 evening

For whoever picks this up next. Plain English, no prior context assumed.

## What AfterCare is

A caregiver photographs an Indian hospital discharge summary. The app turns it into a
picture-and-voice medicine schedule (screen text in the family's language, spoken audio in
Hindi). Box Check compares photographed medicine strips against the prescription. A missed
dose alerts the family. There is a printable fridge sheet.

Safety rules the whole product is built on: never change a dose, never fill in a blank the
paper does not have, never call a strip "safe".

## Where things stand

**The backend is finished, deployed and working.** Region ap-south-1, account 791725739974,
CloudFormation stack "Aftercare". Last deployed 2026-09-20 20:31 IST with the final review
fixes in it.

Live values (also in `web/env.example`):

| Item | Value |
|---|---|
| API | https://ctj5ower7vmwubklgwntkqdwsi0aemrx.lambda-url.ap-south-1.on.aws |
| Uploads bucket | aftercare-docsa50029d5-mjqnfuxpq0xu |
| Cognito pool | ap-south-1_UQXeokR8X |
| Cognito client | 5u4d70pcibfkqq77d3qmccjneh |

**Tested live and passing** (caregiver side, browser against the deployed backend):
join by invite, schedule in Kannada, Given recorded in the database, Hindi audio with drug
names left in English letters, family view percentages, red flags, fridge sheet, settings,
and "delete data on this device" clearing the offline cache.

**Not yet tested live:** everything an owner does, because it needs a real email login.
That means sign-in, photo upload, extraction, confirming flagged lines, activating a plan,
and inviting a caregiver. Box Check has also never run on real strip photos.

## Code layout

- `api/` single Python Lambda, one file per area. `handler.py` routes.
- `infra/` CDK stack.
- `scripts/seed_demo.py` resets the demo circle and prints a caregiver invite link.
- `web/` Next.js 15 static PWA.
- `docs/frontend-handoff.md` the frontend's spec: every screen, every call, the error table
  and the UI rules. Read this before touching `web/`.
- `docs/spec.md` product and safety rules.
- `.superpowers/sdd/2026-09-18-aftercare/` review reports and the work ledger.

## Git state, read this first

- `main` has one commit that is **not pushed**: the backend review fixes (already deployed).
- The frontend fixes live on branch **`worktree-agent-a130d74c62adbd9f4`**, 10 commits, not
  merged into `main`. They fix 18 review findings, including a fake-login backdoor that
  showed invented medicines and invented Box Check verdicts.
- So: merge that branch into `main`, then push both. Nothing else is in flight.

```bash
git checkout main
git merge worktree-agent-a130d74c62adbd9f4
git push origin main
```

## Running things

**Backend deploys must run on the Windows laptop**, because the AWS credentials live there.
From the repo root in PowerShell:

```powershell
.\infra\build.ps1; npx -y aws-cdk@2 deploy Aftercare
```

Backend tests, same machine:

```powershell
.venv\Scripts\python -m pytest -q -m "not golden"
```

410 tests pass as of now.

**The frontend runs anywhere, including a Mac.** Clone the repo, then:

```bash
cd web
cp env.example .env.local
npm install
npm run dev
```

It talks to the deployed backend, so a Mac needs no AWS credentials.

Reset the demo data and get a fresh caregiver invite link (Windows laptop, AWS creds needed):

```powershell
.venv\Scripts\python -m scripts.seed_demo
```

Pass `--web-origin https://your-site` when the frontend is deployed. Each invite link works
once. The demo circle is `ci_demo`, plan `pl_demo`, five medicines, doses seeded from three
days ago with one deliberate missed dose.

## What is left, in order

1. **Merge and push** the frontend branch as above.
2. **Owner run-through**, the big one. Start the frontend, open `/setup/`, sign in with an
   email address verified in SES, create a circle, photograph a prescription, let it extract
   (up to about two minutes), confirm every amber line, activate, then make a caregiver
   invite. This is the first time the owner path runs end to end, so expect to find things.
3. **Box Check with real strips.** Photograph 3 or 4 medicine strips, including one that is
   not on the prescription, so the "do not take" result appears on camera.
4. **Push notifications.** Turn on reminders in `/settings/`, then have someone run the
   reminder function so a real notification arrives.
5. **Deploy the frontend to Amplify.** Afterwards put the real site address into
   `infra/config.py` as `WEB_ORIGIN` and redeploy the backend, so alert emails link to the
   real site. The invite link itself is already built from whatever address the app runs on.
6. **SES email verification.** The AWS account is still in SES sandbox, so login codes and
   alert emails only reach verified addresses. `abhilashreddymand@gmail.com` is verified.
   Every other address used in the demo or video must be verified first, from the SES console
   in ap-south-1, and each person clicks the link AWS emails them.
7. **Demo video and the Builder Center writeup.**

## Things to know before you change anything

- **Money.** Everything runs on credits. Do not enable AWS Marketplace models, do not buy a
  domain, do not call Cost Explorer, do not add a support plan.
- **WhatsApp alerts are built but switched off.** Leave them off unless the owner of the
  account says otherwise.
- **Never print or copy the AWS credentials, the push signing key in SSM, or invite tokens.**
- **Mistral Large 3 on Bedrock does the reading**, with Amazon Textract supplying the words.
  Do not swap in an Anthropic or OpenAI model on Bedrock: those need a Marketplace agreement.
- The measured extraction accuracy is 91% on medicine names and 83% on strengths, and
  anything the model is unsure about is flagged amber for a human to confirm. That is the
  design, not a bug.

## Known gaps, deliberately not fixed

- Box Check can mismatch a salt against its elemental name, for example calcium carbonate
  versus elemental calcium.
- Uploads accept JPEG and PNG only, not PDF.
- There is no "list my circles" endpoint, so an owner who clears their browser data loses the
  link to their circle.
- The extraction Lambda is capped at two minutes, which is enough for a one or two page
  discharge summary.

## Timing

The 14:00 IST Sunday freeze written into `docs/spec.md` was self-imposed and has passed. The
actual hackathon submission deadline was not published when the spec was written, so check
the WeMakeDevs hackathon page before planning the video.
