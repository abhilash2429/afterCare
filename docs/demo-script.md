# AfterCare demo script, under 3 minutes, English, live site

Site: **https://main.d2nozesb14q5me.amplifyapp.com**

No logins happen on camera. You sign in before you start, and the browser stays signed in.

## Login details

**Owner (you).** Open `/setup/`, type `abhilashreddymand@gmail.com`, press **Email me a code**.
An 8-digit code arrives from AWS within a minute. Type it in the Code box, press **Confirm code**.
The screen now says "We emailed a code to that address" so you know it sent.

That address is the only one verified in SES, so codes reach it and nothing else. The session
stays in that browser, so sign in once, well before the demo, and do not clear browsing data.

Your circle is **Sharma family**, English, with an active 4-medicine plan already in it.

**Caregiver (the second tab).** No password ever. A one-time link is the whole login. Mint one
on the Windows laptop, paste it into a second browser tab before the demo, and that tab is then
a caregiver forever:

```powershell
.venv\Scripts\python -m scripts.seed_demo --language en --web-origin https://main.d2nozesb14q5me.amplifyapp.com
```

It prints `caregiver invite: https://...` and resets the demo circle: 5 medicines, three days of
history, yesterday's night dose deliberately missed, today's doses pending. Open the link once,
in the tab you will demo from. Each link works only once, so mint a new one if you reopen it.

## Set up before you hit record

Three tabs, in this order:

- **Tab A — owner.** `https://main.d2nozesb14q5me.amplifyapp.com/upload/`, signed in as above.
- **Tab B — caregiver.** The invite link, opened once, then left on `/schedule/`.
- **Tab C — safety net.** `https://main.d2nozesb14q5me.amplifyapp.com/schedule/` in the owner
  tab's browser, showing the plan that is already active. If the live reading is slow or fails,
  switch here and carry on as if nothing happened.

Have `C:\Users\abhii\Desktop\aftercare-demo\case02.png` ready. That is the discharge summary you
upload. It reads as 4 medicines: Zerodol-P and Ultracet come back clean, Pan and Augmentin 625
Duo come back amber. Measured time from pressing Read to the review screen: **43 seconds**.

## The script

**0:00 – 0:20 — the problem.** Tab A, on the home page.

> A family leaves an Indian hospital with a discharge summary and a bag of strips. The person
> who actually gives the medicines often cannot read that page. Most missed doses after
> discharge are not stubbornness, they are not being able to read the paper.

**0:20 – 0:35 — photograph the paper.** Press **Photograph the page**, pick `case02.png`, press
**Read these pages**.

> One photo of the page the hospital already gave them. No typing, no account for the caregiver.

**0:35 – 1:15 — talk while it reads.** It takes about 40 seconds. Say this, do not sit silent:

> Textract pulls every word with its position on the page. Mistral Large on Bedrock turns those
> words into medicines, and every value has to point back to words actually printed on the page.
> If the page does not say the strength, the app leaves it blank. It never guesses a dose.

**1:15 – 1:45 — review.** The review screen appears.

> Four medicines. Two it read cleanly. Two are amber, and amber lines do not start until a human
> confirms them. Tap the picture and you see the exact line on the photo it came from.

Tap one crop, then press **I checked this line** on both amber cards.

**1:45 – 2:00 — activate.** Press **Activate schedule**.

> That just created the schedule and the reminders for every dose.

**2:00 – 2:25 — the caregiver.** Switch to **Tab B**.

> This is the caregiver's phone. She never signed up. She opened a link once.

Point at the grid: one column per time of day, take or skip per medicine. Press **Given** on a
dose, then press **Hear the schedule** and let the voice play for a few seconds.

> One tap when the dose is given. And the schedule speaks, because reading small print at eight
> in the evening is the actual barrier.

**2:25 – 2:45 — the family.** Press **Family view**.

> Seven days. Yesterday's night dose was missed, and when that happens the family gets a
> notification and an email, so somebody can pick up the phone. The son in another city can see
> everything and change nothing.

**2:45 – 3:00 — close.** Press **Fridge sheet**, then say:

> Print that for the fridge for the grandmother who does not use a phone at all. Three promises:
> we never change a dose, we never fill in a blank the paper does not have, and Box Check never
> tells you a strip is safe.

## If something goes wrong

- **Reading takes too long.** Keep talking through the architecture, or switch to Tab C and say
  "here is one I read earlier".
- **The caregiver tab has logged out.** Mint a new invite with the command above.
- **The voice does not play.** Check the browser volume; press the speaker again. Do not reload.
- **Never** type a 4-digit number expecting it to open anything. That fake login was removed.

## What not to show

- Box Check, unless you have real medicine strips in hand. It needs a photo of strips to say
  anything, and photographing the prescription instead produces nonsense.
- Push notifications, unless you tested them on that exact phone beforehand.
- Any language other than English, unless you have rehearsed it. The demo circle and your own
  circle are both set to English right now.
