import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def drugs_table():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="ap-south-1")
        ddb.create_table(
            TableName="aftercare-drugs",
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"},
                       {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"},
                                  {"AttributeName": "SK", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST")
        t = ddb.Table("aftercare-drugs")
        t.put_item(Item={"PK": "ecos", "SK": "ecosprin", "brand": "Ecosprin 75",
                         "molecules": [{"name": "aspirin", "strengthMg": "75", "unit": "mg"}]})
        t.put_item(Item={"PK": "vitd", "SK": "vitd3 shot", "brand": "VitD3 Shot",
                         "molecules": [{"name": "vitamin d3", "strengthMg": "60000", "unit": "iu"}]})
        import api.drugs_repo as repo
        repo._table = t
        yield t
        repo._table = None


def test_lookup_known_brand(drugs_table):
    from api.drugs_repo import lookup_brand
    mols = lookup_brand("Tab. Ecosprin 75mg")
    assert mols[0].name == "aspirin" and mols[0].strengthMg == 75


def test_lookup_typo_still_matches(drugs_table):
    from api.drugs_repo import lookup_brand
    assert lookup_brand("Ecosprn")[0].name == "aspirin"


def test_unknown_brand_returns_empty(drugs_table):
    from api.drugs_repo import lookup_brand
    assert lookup_brand("Zzzqqx") == []


def test_lookup_preserves_non_mg_unit(drugs_table):
    from api.drugs_repo import lookup_brand
    mols = lookup_brand("VitD3 Shot")
    assert mols[0].name == "vitamin d3"
    assert mols[0].strengthMg == 60000
    assert mols[0].unit == "iu"


def test_lookup_blank_brand_returns_empty(drugs_table):
    from api.drugs_repo import lookup_brand
    assert lookup_brand("") == []


def test_lookup_never_raises_on_query_error(monkeypatch, drugs_table):
    from api.drugs_repo import lookup_brand
    import api.drugs_repo as repo

    def boom(*a, **k):
        raise RuntimeError("dynamo down")

    monkeypatch.setattr(repo._table, "query", boom)
    assert lookup_brand("Ecosprin 75") == []


def test_lookup_finds_item_past_first_300_in_bucket(drugs_table):
    # Regression: an old Limit=300 on the bucket query silently dropped any
    # item sorting after the first 300 SKs. "zzbrtarget" sorts after all 305
    # "zzbrfiller####" SKs (f < t), so it must still be found.
    from api.drugs_repo import lookup_brand
    with drugs_table.batch_writer() as batch:
        for i in range(305):
            batch.put_item(Item={
                "PK": "zzbr", "SK": "zzbrfiller%04d" % i,
                "brand": "filler", "molecules": []})
        batch.put_item(Item={
            "PK": "zzbr", "SK": "zzbrtarget", "brand": "Zzbrtarget",
            "molecules": [{"name": "targetmol", "strengthMg": "10", "unit": "mg"}]})
    mols = lookup_brand("Zzbrtarget")
    assert mols and mols[0].name == "targetmol"


def test_bucket_items_pages_on_last_evaluated_key(monkeypatch, drugs_table):
    import api.drugs_repo as repo

    page1 = {"Items": [{"PK": "pgtb", "SK": "pgtbitem1"}],
             "LastEvaluatedKey": {"PK": "pgtb", "SK": "pgtbitem1"}}
    page2 = {"Items": [{"PK": "pgtb", "SK": "pgtbitem2",
                        "molecules": [{"name": "found", "strengthMg": "5", "unit": "mg"}]}]}
    calls = {"n": 0}

    def fake_query(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            assert "ExclusiveStartKey" not in kwargs
            return page1
        assert kwargs["ExclusiveStartKey"] == {"PK": "pgtb", "SK": "pgtbitem1"}
        return page2

    monkeypatch.setattr(repo._table, "query", fake_query)
    items = repo._bucket_items("pgtb")
    assert set(items) == {"pgtbitem1", "pgtbitem2"}
    assert calls["n"] == 2


def test_lookup_strength_zero_is_not_dropped(drugs_table):
    from api.drugs_repo import lookup_brand
    drugs_table.put_item(Item={"PK": "zero", "SK": "zerodrug", "brand": "Zerodrug",
                               "molecules": [{"name": "placebo", "strengthMg": "0", "unit": "mg"}]})
    mols = lookup_brand("Zerodrug")
    assert mols[0].strengthMg == 0.0


def test_etl_rows_preserves_zero_strength(tmp_path):
    # Regression: `if m.strengthMg else None` treats a real 0mg strength as
    # falsy and silently drops it to None. Must store "0.0", not None.
    import csv
    from data.etl_drugs import rows

    csv_path = tmp_path / "sample.csv"
    fieldnames = ["id", "name", "price(₹)", "Is_discontinued", "manufacturer_name",
                  "type", "pack_size_label", "short_composition1", "short_composition2"]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerow({"id": "1", "name": "Placebo Tablet", "price(₹)": "10",
                    "Is_discontinued": "False", "manufacturer_name": "Acme",
                    "type": "tablet", "pack_size_label": "strip of 10",
                    "short_composition1": "Placebo (0mg)", "short_composition2": ""})
    item = next(rows(str(csv_path)))
    assert item["molecules"][0]["strengthMg"] == "0.0"


def test_failure_after_first_page_returns_empty(monkeypatch, drugs_table):
    import api.drugs_repo as repo
    real = repo._table.query
    calls = []

    def flaky(**kw):
        calls.append(1)
        if len(calls) > 1:
            raise RuntimeError("throttled")
        res = real(**kw)
        res["LastEvaluatedKey"] = {"PK": "ecos", "SK": "ecosprin"}
        return res

    monkeypatch.setattr(repo._table, "query", flaky)
    assert repo.lookup_brand("Ecosprin 75") == []


def test_ambiguous_brand_returns_nothing(drugs_table):
    from api.drugs_repo import lookup_brand
    drugs_table.put_item(Item={"PK": "levo", "SK": "levolin", "brand": "Levolin",
                               "ambiguous": True, "molecules": []})
    assert lookup_brand("Levolin") == []


def test_etl_marks_brands_with_conflicting_molecules_ambiguous(tmp_path):
    from data.etl_drugs import merged
    csv_path = tmp_path / "m.csv"
    csv_path.write_text(
        "id,name,price,Is_discontinued,manufacturer_name,type,pack_size_label,"
        "short_composition1,short_composition2\n"
        "1,Levolin 1 Tablet,1,FALSE,A,allopathy,strip,Levosalbutamol (1mg),\n"
        "2,Levolin 5 Tablet,1,FALSE,B,allopathy,strip,Levocetirizine (5mg),\n"
        "3,PAN 40 Tablet,1,FALSE,C,allopathy,strip,Pantoprazole (40mg),\n"
        "4,PAN 20 Tablet,1,FALSE,C,allopathy,strip,Pantoprazole (20mg),\n",
        encoding="utf-8")
    items = merged(str(csv_path))
    assert items[("levo", "levolin")]["ambiguous"] is True
    assert items[("levo", "levolin")]["molecules"] == []
    assert not items[("pan", "pan")].get("ambiguous")
