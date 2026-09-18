import aws_cdk as cdk

from infra import config
from infra.aftercare_stack import AftercareStack

app = cdk.App()
AftercareStack(app, "Aftercare", env=cdk.Environment(account=config.ACCOUNT, region=config.REGION))
app.synth()
