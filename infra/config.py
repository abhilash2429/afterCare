REGION = "ap-south-1"
ACCOUNT = "791725739974"
TABLE_NAME = "aftercare"
DRUGS_TABLE_NAME = "aftercare-drugs"

# Task 9 bake-off winner. On-demand in ap-south-1 (aws bedrock list-foundation-models).
BEDROCK_MODEL_ID = "mistral.mistral-large-3-675b-instruct"
# From: aws bedrock list-inference-profiles --region ap-south-1
BEDROCK_CHEAP_MODEL_ID = "apac.amazon.nova-lite-v1:0"

# Verified SES identity in ap-south-1; Cognito sends email OTPs from it.
SES_FROM_EMAIL = "abhilashreddymand@gmail.com"

# Base URL of the PWA; invite links are built on it. Placeholder until Amplify is set up.
WEB_ORIGIN = "https://main.d2nozesb14q5me.amplifyapp.com"

# SSM parameter names (not values) holding the VAPID keypair. Created out-of-band by
# scripts/make_vapid.py's printed `aws ssm put-parameter` commands, never by CDK.
VAPID_PRIVATE_PARAM = "/aftercare/vapid/private"
VAPID_PUBLIC_PARAM = "/aftercare/vapid/public"

# Money rule R42: WhatsApp (Meta pass-through fees may not be credit-covered) ships
# behind a flag defaulting OFF. Flip to "true" only after an explicit user opt-in.
WHATSAPP_ENABLED = "false"

# ApiUrl (deployed): https://ctj5ower7vmwubklgwntkqdwsi0aemrx.lambda-url.ap-south-1.on.aws/
