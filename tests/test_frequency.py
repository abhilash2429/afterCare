import pytest
from api.frequency import parse_frequency


@pytest.mark.parametrize("text,slots,prn", [
    ("OD", ["morning"], False),
    ("o.d.", ["morning"], False),
    ("BD", ["morning", "night"], False),
    ("bid", ["morning", "night"], False),
    ("TDS", ["morning", "noon", "night"], False),
    ("TID", ["morning", "noon", "night"], False),
    ("QID", ["morning", "noon", "night", "bedtime"], False),
    ("HS", ["bedtime"], False),
    ("nocte", ["bedtime"], False),
    ("1-0-1", ["morning", "night"], False),
    ("1-1-1", ["morning", "noon", "night"], False),
    ("0-0-1", ["night"], False),
    ("1-1-1-1", ["morning", "noon", "night", "bedtime"], False),
    ("SOS", [], True),
    ("PRN", [], True),
    ("as needed", [], True),
    ("", [], False),
    ("weekly", [], False),
    ("alternate days", [], False),
    ("3.5 ml BD", ["morning", "night"], False),
    ("2 puffs BD", ["morning", "night"], False),
    ("1 tab 1-0-1", ["morning", "night"], False),
    ("2.5 ml SOS", [], True),
    ("5 days", [], False),
])
def test_parse_frequency(text, slots, prn):
    assert parse_frequency(text) == (slots, prn)
