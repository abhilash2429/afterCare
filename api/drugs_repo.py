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


def lookup_brand(brand_text):
    """Brand text -> molecules. Unknown brands return [] rather than raising."""
    norm = normalise_brand(brand_text)
    if not norm:
        return []
    try:
        res = _t().query(
            KeyConditionExpression="PK = :p",
            ExpressionAttributeValues={":p": bucket_key(norm)},
            Limit=300)
    except Exception:
        return []
    items = {i["SK"]: i for i in res.get("Items", [])}
    name, _score = best_brand_match(norm, list(items))
    if not name:
        return []
    out = []
    for m in items[name].get("molecules", []):
        strength = m.get("strengthMg")
        out.append(Molecule(name=m["name"],
                            strengthMg=float(strength) if strength else None,
                            unit=m.get("unit") or "mg"))
    return out
