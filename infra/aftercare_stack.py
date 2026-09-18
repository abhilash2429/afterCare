from aws_cdk import (Stack, Duration, RemovalPolicy, CfnOutput,
                     aws_s3 as s3, aws_dynamodb as ddb, aws_lambda as lambda_,
                     aws_iam as iam, aws_logs as logs, aws_cognito as cognito,
                     aws_secretsmanager as secretsmanager)
from constructs import Construct

from infra import config


class AftercareStack(Stack):
    def __init__(self, scope: Construct, cid: str, **kw):
        super().__init__(scope, cid, **kw)

        docs = s3.Bucket(
            self, "Docs",
            encryption=s3.BucketEncryption.KMS_MANAGED,
            bucket_key_enabled=True,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(30))],
            cors=[s3.CorsRule(allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET],
                              allowed_origins=["*"], allowed_headers=["*"])],
            removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)

        table = ddb.Table(
            self, "Table", table_name=config.TABLE_NAME,
            partition_key=ddb.Attribute(name="PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="SK", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expiresAt",
            removal_policy=RemovalPolicy.DESTROY)

        drugs = ddb.Table(
            self, "Drugs", table_name=config.DRUGS_TABLE_NAME,
            partition_key=ddb.Attribute(name="PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="SK", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY)

        pool = cognito.UserPool(
            self, "Users", sign_in_aliases=cognito.SignInAliases(email=True),
            self_sign_up_enabled=True, feature_plan=cognito.FeaturePlan.ESSENTIALS,
            sign_in_policy=cognito.SignInPolicy(
                allowed_first_auth_factors=cognito.AllowedFirstAuthFactors(
                    password=True, email_otp=True)),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY)
        client = pool.add_client("Web", auth_flows=cognito.AuthFlow(user=True),
                                 disable_o_auth=True, prevent_user_existence_errors=True)

        circle_secret = secretsmanager.Secret(
            self, "CircleTokenSecret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True, password_length=64),
            removal_policy=RemovalPolicy.DESTROY)

        env = {"TABLE_NAME": table.table_name, "DRUGS_TABLE_NAME": drugs.table_name,
               "DOCS_BUCKET": docs.bucket_name,
               "BEDROCK_MODEL_ID": config.BEDROCK_MODEL_ID,
               "BEDROCK_CHEAP_MODEL_ID": config.BEDROCK_CHEAP_MODEL_ID}

        api = lambda_.Function(
            self, "Api", runtime=lambda_.Runtime.PYTHON_3_12,
            handler="api.handler.lambda_handler",
            code=lambda_.Code.from_asset("build/api"),
            timeout=Duration.seconds(120), memory_size=1024,
            environment={**env, "USER_POOL_ID": pool.user_pool_id,
                         "USER_POOL_CLIENT_ID": client.user_pool_client_id,
                         "CIRCLE_SECRET_ARN": circle_secret.secret_arn,
                         "WEB_ORIGIN": config.WEB_ORIGIN},
            log_group=logs.LogGroup(
                self, "ApiLogs", retention=logs.RetentionDays.TWO_WEEKS,
                removal_policy=RemovalPolicy.DESTROY))

        reminder = lambda_.Function(
            self, "Reminder", runtime=lambda_.Runtime.PYTHON_3_12,
            handler="api.reminder.lambda_handler",
            code=lambda_.Code.from_asset("build/api"),
            timeout=Duration.seconds(60), memory_size=512, environment=env,
            log_group=logs.LogGroup(
                self, "ReminderLogs", retention=logs.RetentionDays.TWO_WEEKS,
                removal_policy=RemovalPolicy.DESTROY))

        for fn in (api, reminder):
            table.grant_read_write_data(fn)
            drugs.grant_read_data(fn)
            docs.grant_read_write(fn)
            fn.add_to_role_policy(iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "textract:AnalyzeDocument",
                         "translate:TranslateText", "polly:SynthesizeSpeech",
                         "ses:SendEmail", "social-messaging:SendWhatsAppMessage"],
                resources=["*"]))

        circle_secret.grant_read(api)

        api.add_to_role_policy(iam.PolicyStatement(
            actions=["scheduler:CreateSchedule", "scheduler:DeleteSchedule"],
            resources=["*"]))
        api.add_to_role_policy(iam.PolicyStatement(
            actions=["iam:PassRole"],
            resources=["*"],
            conditions={"StringEquals": {"iam:PassedToService": "scheduler.amazonaws.com"}}))

        url = api.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,
            cors=lambda_.FunctionUrlCorsOptions(
                allowed_origins=["*"],
                allowed_methods=[lambda_.HttpMethod.ALL],
                allowed_headers=["content-type", "authorization"]))

        CfnOutput(self, "ApiUrl", value=url.url)
        CfnOutput(self, "DocsBucket", value=docs.bucket_name)
        CfnOutput(self, "ReminderArn", value=reminder.function_arn)
        CfnOutput(self, "UserPoolId", value=pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=client.user_pool_client_id)
