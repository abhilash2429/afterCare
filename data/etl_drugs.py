"""Load the Kaggle A-Z India medicine CSV into the aftercare-drugs table.

Usage: python -m data.etl_drugs data/drugs_raw/medicine_dataset.csv
"""
import csv
import sys

import boto3

from api.drugs import bucket_key, normalise_brand, normalise_molecule, parse_composition

TABLE = "aftercare-drugs"


def rows(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            name = row.get("name") or ""
            norm = normalise_brand(name)
            if not norm:
                continue
            comp = " + ".join(x for x in (row.get("short_composition1"),
                                          row.get("short_composition2")) if x)
            molecules = parse_composition(comp)
            if not molecules:
                continue
            yield {
                "PK": bucket_key(norm), "SK": norm, "brand": name.strip(),
                "manufacturer": (row.get("manufacturer_name") or "").strip(),
                "packSize": (row.get("pack_size_label") or "").strip(),
                "discontinued": str(row.get("Is_discontinued", "")).lower() == "true",
                "molecules": [{"name": m.name,
                               "strengthMg": str(m.strengthMg) if m.strengthMg is not None else None,
                               "unit": m.unit}
                              for m in molecules],
            }


def _names(item):
    return frozenset(normalise_molecule(m["name"]) for m in item["molecules"])


def merged(path):
    """One item per normalised brand. A brand whose rows disagree on the molecules
    (Levolin is levosalbutamol from one maker, levocetirizine from another) is stored
    ambiguous with no molecules, so a lookup can never pick one of them silently."""
    out = {}
    for item in rows(path):
        key = (item["PK"], item["SK"])
        first = out.get(key)
        if first is None:
            out[key] = item
        elif not first.get("ambiguous") and _names(first) != _names(item):
            first["ambiguous"], first["molecules"] = True, []
    return out


_STALE_PRUNE_GUARD = 0.05  # a bigger stale fraction smells like a bad/truncated source CSV


def _should_prune_stale(stale_count, written):
    """False guards against wiping the table when the source CSV looks wrong: more than
    5% of what was just written showing up as stale to delete is not a normal refresh."""
    return not (written and stale_count > _STALE_PRUNE_GUARD * written)


def main(path):
    table = boto3.resource("dynamodb", region_name="ap-south-1").Table(TABLE)
    items = merged(path)
    written = 0
    with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
        for item in items.values():
            batch.put_item(Item=item)
            written += 1
            if written % 10000 == 0:
                print("written", written, flush=True)
    stale, scan = [], {"ProjectionExpression": "PK, SK"}
    while True:
        page = table.scan(**scan)
        stale += [(i["PK"], i["SK"]) for i in page["Items"] if (i["PK"], i["SK"]) not in items]
        if "LastEvaluatedKey" not in page:
            break
        scan["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    if _should_prune_stale(len(stale), written):
        with table.batch_writer() as batch:
            for pk, sk in stale:
                batch.delete_item(Key={"PK": pk, "SK": sk})
        removed = len(stale)
    else:
        print("WARNING: %d stale rows is more than %.0f%% of %d written - skipping delete, "
              "check the source CSV" % (len(stale), _STALE_PRUNE_GUARD * 100, written),
              flush=True)
        removed = 0
    print("done", written, "ambiguous", sum(1 for i in items.values() if i.get("ambiguous")),
          "stale removed", removed)


if __name__ == "__main__":
    main(sys.argv[1])
