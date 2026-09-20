# AfterCare, Builder Center submission answers

## What does your project do?

AfterCare turns an Indian hospital discharge summary into a medicine schedule the person who
actually gives the medicines can follow.

A family member photographs the discharge page. AfterCare reads it and shows the same
medicines as a picture schedule, one column per time of day, and speaks the next dose out loud.
A caregiver taps Given when a dose is taken. If a dose is missed, the family is notified by
browser push and email, so somebody can pick up the phone. Box Check compares a photo of the
medicine strips the family actually bought against the prescription, and says matches, look
again, or do not take. There is a printable fridge sheet for households that do not use phones.

The problem: after discharge, the instructions live on one sheet of paper, in clinical English,
often abbreviated. The person giving the medicines is frequently an elderly spouse, a domestic
helper, or a relative who cannot read that page. Missed and doubled doses after discharge are
usually a reading problem, not a compliance problem. The people who need this are Indian
families caring for someone at home after a hospital stay, and the adult children in another
city who worry about it.

Three rules the product is built on: never change a dose, never fill in a blank the paper does
not have, and never tell anyone a strip is safe. Every medical value shown has to trace back to
words actually printed on the photographed page. Anything the model is not sure about is marked
amber and does not start until a human confirms it. Measured on our ten-case golden set:
91% accuracy on medicine names, 83% on strengths, and every remaining error was on a line
already flagged for human confirmation.

## How did you use AWS in your project?

**Build it, AWS open source stack**

- **AWS CDK (Python)** defines the entire stack: Lambda functions, DynamoDB table, S3 bucket,
  Cognito user pool, EventBridge Scheduler group, IAM roles and least-privilege policies. One
  `cdk deploy` reproduces the whole backend.
- **AWS SDK for Python (boto3)** in the Lambda code for every service call.
- **Amplify JS library (aws-amplify v6)** in the Next.js PWA for Cognito email-code sign-in
  (`USER_AUTH` flow with the `EMAIL_OTP` challenge).
- **AWS CLI v2** for deployment of the static site and for operational checks.
- **moto** to run 410 unit tests against fake AWS services locally, with no cloud calls in CI.

**Ship it, AWS services**

- **Amazon Textract** (`DetectDocumentText`) extracts every word from the photographed page
  with its bounding box. The word geometry is what makes the safety model possible: each
  medicine line is checked against the words actually printed, and the app can show the exact
  crop of the photo a value came from.
- **Amazon Bedrock** (`Converse` API, Mistral Large 3) turns those grounded words into
  structured medicines. The model only chooses among words Textract found; anything it returns
  that is not printed on the page is rejected or flagged.
- **AWS Lambda** with a **Lambda Function URL** runs the whole API, a single Python 3.12
  function with its own router. A second Lambda handles reminders and escalation.
- **Amazon DynamoDB**, one table, single-table design with TTL: circles, members, plans, doses,
  documents, invites and audit records, with documents, invites and audit rows expiring
  automatically.
- **Amazon S3** stores the photographed pages and generated audio, with presigned URLs so
  photos upload straight from the browser and never pass through the API.
- **Amazon Cognito** authenticates owners with an emailed code, no passwords. Caregivers never
  sign up at all: they open a one-time invite link that mints a signed session token.
- **Amazon EventBridge Scheduler** creates a one-shot schedule per dose, in Asia/Kolkata, with
  `ActionAfterCompletion: DELETE` so each reminder cleans itself up. A follow-up check schedule
  fires after the family's chosen escalation window.
- **Amazon Polly** (neural, Kajal) speaks the schedule. **Amazon Translate** translates only the
  surrounding wording, never the drug names, which a general translation service cannot be
  trusted with.
- **Amazon SES** sends the missed-dose escalation email to the family.
- **AWS Systems Manager Parameter Store** (SecureString) holds the Web Push signing key and
  **AWS Secrets Manager** holds the caregiver session-token secret.
- **AWS Amplify Hosting** serves the static Next.js PWA over HTTPS.
- **Amazon CloudWatch Logs** for both functions, with patient data and tokens redacted before
  logging.

## Blog links

<one AWS Builder Center blog URL per team member, optional>

## Team leader's contributions

Abhilash Reddy, backend, infrastructure and product safety.

- Designed the product and its safety rules: never change a dose, never fill a blank, never call
  a strip safe, and the grounding model that enforces them in code.
- Built the entire backend: the single-Lambda API and its router, the Textract plus Bedrock
  extraction pipeline with token-level grounding checks, plan validation and activation, the
  dose and reminder engine on EventBridge Scheduler, escalation over Web Push and SES, Box Check
  strip matching, the drug dataset and its ETL, speech with Polly and Translate, and the
  Cognito plus invite-token auth model.
- Wrote the infrastructure as AWS CDK, including least-privilege IAM, and ran every deployment.
- Built the ten-case golden evaluation set and the accuracy gate used to tune extraction to 91%
  on names and 83% on strengths.
- Ran the final code and security review of the whole codebase, fixed the findings, and verified
  the live system end to end in a browser against the deployed backend.
- 410 automated tests.

## Second team member's contributions

Suprith, frontend and presentation.

- Built the Next.js 15 static PWA: owner setup and sign-in, upload, review and confirm with
  photo crops, the schedule grid, voice playback, Box Check, red flags, fridge sheet, family
  view and settings.
- Implemented the offline behaviour and the service worker, Web Push subscription, and the
  multilingual interface in English, Hindi, Kannada and Telugu.
- Produced the demo video and the Builder Center write-up.

## Help us evaluate you: feedback on the AWS services you used

**Amazon Polly** has no Kannada voice at all, and this is the single biggest gap for an Indian
product. Our target user is often a Kannada-speaking grandmother. We ship her Hindi audio with a
visible label saying so, which is a compromise we should not have had to make. Indic coverage
outside Hindi is thin across the board.

**Amazon Textract** does not read Kannada, Hindi or other Indic scripts. Indian discharge
summaries are frequently bilingual, and anything in the local script is invisible to us. Between
this and Polly, the two services that decide whether an Indian-language product is possible are
the two that do not cover Indian languages.

**Amazon Bedrock** model availability is hard to discover. Which models exist in ap-south-1,
which need a Marketplace subscription, and which need an accepted agreement, are three different
facts spread across three places, and finding a capable model we could use without a Marketplace
agreement took real time. The `Converse` API itself is good, but there is no dependable
structured-output mode, so we wrote our own JSON repair and validation layer.

**Amazon Cognito** email-code sign-in is underdocumented. The `USER_AUTH` flow with
`preferredChallenge: EMAIL_OTP` is barely covered outside API reference pages, and there is no
"sign in or sign up" primitive, so every app has to build the branch itself. Worse for user
experience: with prevent-user-existence-errors on, signing in as a user who does not exist
returns a normal challenge, so the client genuinely cannot tell the difference between a code
being sent and nothing happening. We only caught this by reading network traffic during testing.

**Amazon SES** sandbox rules make hackathon demos painful. Every recipient must individually
verify, which means a demo cannot show a real family member receiving an alert unless that
person clicks a verification email first.

**AWS Amplify Hosting** manual zip deployments failed silently for us. A zip produced by one
common tool deployed only `index.html`, every other file 404'd, and the deployment job still
reported SUCCEED. A partial deployment reporting success is the worst possible failure mode; the
job should validate the artifact and fail loudly.

**AWS Lambda Function URLs** give you one CORS configuration for the whole function, with no
per-route control, and no way to attach a WAF directly. It is otherwise the right primitive for
a small API, and we would like it to stay simple while gaining those two things.

**AWS Systems Manager Parameter Store** SecureString using the default `alias/aws/ssm` key has
no fixed per-account key ARN, so a least-privilege KMS policy cannot pin the resource and has to
fall back to a `kms:ViaService` condition. That is a sharp edge on the exact path where people
are trying to do the secure thing.

**AWS CDK on Windows** assumes Docker for Python bundling. Building Linux wheels without it
requires `--platform manylinux2014_x86_64` and manual handling of packages that publish no
wheels. A documented no-Docker path would have saved us an afternoon.

## What did you like about the AWS services you used?

**Amazon Textract's word-level geometry is the reason this product can exist.** Every word comes
back with a bounding box, and that let us do two things that matter more than anything else:
check every value the model produces against words actually printed on the page, and show the
caregiver the exact crop of their own photo that each line came from. A safety feature we
thought would be hard came directly out of the API response.

**Amazon EventBridge Scheduler** replaced what would have been a cron job plus a state machine.
One-shot `at()` schedules with a timezone, and `ActionAfterCompletion: DELETE` so each schedule
deletes itself after firing, meant per-dose reminders were a few lines of code with nothing left
to clean up.

**AWS Lambda Function URLs with CDK** gave us a public HTTPS API with no API Gateway, no
ALB and no VPC. For a small team this removed an entire layer of configuration.

**Amazon DynamoDB** single-table design with TTL fit this product exactly. Documents, invites
and audit records simply expire, which is data minimisation we did not have to write code for.

**Amazon Bedrock's Converse API** is a genuinely uniform interface. Swapping the model we used
was a one-line configuration change, with no code changes anywhere in the extraction pipeline.

**Amazon Cognito's emailed codes** are the right fit for elderly and low-literacy users: no
password to remember, no password to forget, no password to reset.

**Amazon Polly's neural Kajal voice** sounds like a person rather than a machine, and selecting
the language through `LanguageCode` rather than a different voice made the bilingual setup
straightforward.

**AWS Amplify Hosting** put a static site live with HTTPS in about thirty seconds, with no
pipeline to configure, which was exactly right at hackathon pace.

**AWS CDK** deserves specific praise. The whole backend, including least-privilege IAM policies
that would have been tedious to write by hand, is one Python file we could review like code and
redeploy in under a minute. Paired with **moto**, we tested 410 cases against fake AWS services
with no cloud calls and no credentials in CI.
