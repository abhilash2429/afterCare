import boto3

from api.common import DRUGS_TABLE, REGION
from api.drugs import best_brand_match, bucket_key, normalise_brand
from api.models import Molecule

_table = None


def _t():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb", region_name=REGION).Table(DRUGS_TABLE)
    return _table


def _bucket_items(pk):
    """All items in a PK bucket, paginating past DynamoDB's 1 MB/page limit.
    Never raises: any query failure returns whatever was read so far (possibly none)."""
    items = {}
    start_key = None
    try:
        while True:
            kwargs = {
                "KeyConditionExpression": "PK = :p",
                "ExpressionAttributeValues": {":p": pk},
            }
            if start_key:
                kwargs["ExclusiveStartKey"] = start_key
            res = _t().query(**kwargs)
            for i in res.get("Items", []):
                items[i["SK"]] = i
            start_key = res.get("LastEvaluatedKey")
            if not start_key:
                break
    except Exception:
        pass
    return items


def lookup_brand(brand_text):
    """Brand text -> molecules. Unknown brands return [] rather than raising."""
    norm = normalise_brand(brand_text)
    if not norm:
        return []
    items = _bucket_items(bucket_key(norm))
    name, _score = best_brand_match(norm, list(items))
    if not name:
        return []
    out = []
    for m in items[name].get("molecules", []):
        strength = m.get("strengthMg")
        out.append(Molecule(name=m["name"],
                            strengthMg=float(strength) if strength is not None else None,
                            unit=m.get("unit") or "mg"))
    return out
