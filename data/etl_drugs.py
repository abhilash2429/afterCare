"""Load the Kaggle A-Z India medicine CSV into the aftercare-drugs table.

Usage: python data/etl_drugs.py data/drugs_raw/medicine_dataset.csv
"""
import csv
import sys

import boto3

from api.drugs import bucket_key, normalise_brand, parse_composition

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
                               "strengthMg": str(m.strengthMg) if m.strengthMg else None,
                               "unit": m.unit}
                              for m in molecules],
            }


def main(path):
    table = boto3.resource("dynamodb", region_name="ap-south-1").Table(TABLE)
    seen, written = set(), 0
    with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
        for item in rows(path):
            key = (item["PK"], item["SK"])
            if key in seen:
                continue
            seen.add(key)
            batch.put_item(Item=item)
            written += 1
            if written % 10000 == 0:
                print("written", written, flush=True)
    print("done", written)


if __name__ == "__main__":
    main(sys.argv[1])
