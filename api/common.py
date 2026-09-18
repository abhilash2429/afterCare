import os
import uuid
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

TABLE = os.environ.get("TABLE_NAME", "aftercare")
DRUGS_TABLE = os.environ.get("DRUGS_TABLE_NAME", "aftercare-drugs")
BUCKET = os.environ.get("DOCS_BUCKET", "")
REGION = os.environ.get("AWS_REGION", "ap-south-1")


def new_id(prefix):
    return "%s_%s" % (prefix, uuid.uuid4().hex[:12])


def now_ist():
    return datetime.now(IST)


def redact(value):
    """Only shape reaches the logs, never content."""
    if value is None:
        return "None"
    s = str(value)
    return "<%s len=%d>" % (type(value).__name__, len(s))
