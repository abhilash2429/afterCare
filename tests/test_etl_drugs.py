import importlib.util
import os

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
_spec = importlib.util.spec_from_file_location("etl_drugs", os.path.join(DATA, "etl_drugs.py"))
etl_drugs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(etl_drugs)


# Minor 9: skip the prune when stale rows are more than 5% of what was just written -
# that smells like a bad/truncated source CSV, not a normal refresh.
def test_should_prune_stale_guards_against_a_bad_source_csv():
    assert etl_drugs._should_prune_stale(3, 100) is True
    assert etl_drugs._should_prune_stale(5, 100) is True
    assert etl_drugs._should_prune_stale(6, 100) is False
    assert etl_drugs._should_prune_stale(0, 0) is True
