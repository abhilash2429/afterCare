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
