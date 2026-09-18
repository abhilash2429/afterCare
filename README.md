# AfterCare

Photograph an Indian hospital discharge summary. Get a picture-and-voice medicine
schedule in your language. Then photograph the strips you bought and check that the
pill box matches the paper.

Built for **First Commit** (WeMakeDevs x AWS Bharat Builds Tour, 17–20 Sep 2026),
**Ship It** track.

> Everyone reads the prescription. We check that the paper matches the pill box.

**AfterCare re-displays what your doctor wrote. It never changes a dose.**

## Why

- Only **31%** of Indian public-hospital discharge notes contain diagnosis,
  medication, lifestyle and follow-up; only **25%** of carers understand them
  ([PLOS ONE](https://doi.org/10.1371/journal.pone.0230438)).
- **70%** of paediatric caregivers do not comply with medication directions
  ([doi:10.1016/j.cegh.2022.101137](https://doi.org/10.1016/j.cegh.2022.101137)).
- **36.8%** of OPD patients poorly understand their prescription and ask for
  vernacular, pictorial formats
  ([doi:10.4103/ijp.ijp_359_24](https://doi.org/10.4103/ijp.ijp_359_24)).

Every existing product turns clinical documents into structure *for the doctor*.
This one is for the person holding the pill box.

## Docs

- [System design and specification](docs/spec.md)
- [Implementation plan](docs/superpowers/plans/2026-09-18-aftercare.md)
- [API contract](docs/api/openapi.yaml)

## Stack

Next.js 15 static-export PWA on Amplify Hosting → Lambda Function URL (Python 3.12) →
Textract (words + boxes) → Bedrock Claude Sonnet 5 (structuring with source citations)
→ DynamoDB → EventBridge Scheduler → Web Push / WhatsApp (AWS End User Messaging
Social) / SES. Amazon Translate and Polly for language and voice. All storage in
`ap-south-1`.

## Layout

```
infra/   CDK (Python)      one stack, ap-south-1
api/     Lambda handlers   Python 3.12
web/     Next.js 15 PWA
data/    drug ETL, synthetic golden document set
docs/    spec, plan, openapi.yaml
```

## Running the tests

```bash
pip install -e ".[dev]"
python -m pytest -v
```

The extraction accuracy gate needs AWS credentials and uploaded photos:

```bash
GOLDEN_S3_PREFIX=circles/ci_demo/golden python -m pytest -m golden -v -s
```

## Data and attribution

- Brand → molecule mapping: *A-Z Medicine Dataset of India*, CC BY-SA 4.0
  ([Kaggle](https://www.kaggle.com/datasets/shudhanshusingh/az-medicine-dataset-of-india)).
- Test documents are **synthetic**. They are generated from the blank NABH E-Mitra
  discharge summary template and filled with invented patients. No real patient data
  exists anywhere in this repository.

## Safety

AfterCare never changes a dose, never suggests a substitute, and never invents a
warning the document does not contain. Anything it cannot read is shown as
"ask doctor". See [spec §7](docs/spec.md#7-safety-rules-non-negotiable) for the rules
and the tests that enforce them.
