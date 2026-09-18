"""Compare extraction models on the golden set.

Render photos: python data/make_docs.py && python scripts/bakeoff.py --render
Bake-off:      DOCS_BUCKET=<bucket> GOLDEN_S3_PREFIX=circles/ci_demo/golden \
               python scripts/bakeoff.py <model_id> [<model_id> ...]
"""
import glob
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def render():
    """data/out/caseNN.html -> data/photos/caseNN.png via headless Edge."""
    photos = os.path.join(ROOT, "data", "photos")
    os.makedirs(photos, exist_ok=True)
    for html in sorted(glob.glob(os.path.join(ROOT, "data", "out", "*.html"))):
        png = os.path.join(photos, os.path.basename(html)[:-5] + ".png")
        if os.path.exists(png):
            os.remove(png)
        profile = tempfile.mkdtemp(prefix="edge_")  # without its own profile Edge writes nothing
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--user-data-dir=" + profile, "--window-size=900,1300",
                        "--screenshot=" + png, "file:///" + html.replace("\\", "/")],
                       capture_output=True, timeout=60)
        for _ in range(60):  # msedge.exe can return before the headless child writes
            if os.path.exists(png) and os.path.getsize(png):
                break
            time.sleep(0.5)
        print("rendered", png, os.path.getsize(png))


def bakeoff(model_id, prefix):
    from api import extract
    from tests.test_golden import FIELDS, GATES, run_gate
    usage = {"calls": 0, "input": 0, "output": 0, "modelMs": 0}
    converse = extract._bedrock.converse

    def counted(**kwargs):
        res = converse(**kwargs)
        usage["calls"] += 1
        usage["input"] += res["usage"]["inputTokens"]
        usage["output"] += res["usage"]["outputTokens"]
        usage["modelMs"] += res["metrics"]["latencyMs"]
        return res

    extract._bedrock.converse = counted
    started = time.time()
    try:
        acc, rows = run_gate(prefix, model_id=model_id)
    finally:
        extract._bedrock.converse = converse
    print("\n==", model_id)
    for case_id, hits, total in rows:
        print(case_id, " ".join("%s=%d/%d" % (f, hits[f], total) for f in FIELDS))
    passed = all(acc[f] >= GATES[f] for f in FIELDS)
    print("ACCURACY", {f: round(acc[f], 3) for f in FIELDS},
          "mean=%.3f" % (sum(acc.values()) / len(FIELDS)), "PASS" if passed else "FAIL")
    print("USAGE", usage, "wall=%.1fs" % (time.time() - started),
          "model_ms_per_doc=%d" % (usage["modelMs"] / max(usage["calls"], 1)))


if __name__ == "__main__":
    if sys.argv[1:] == ["--render"]:
        render()
    else:
        for model in sys.argv[1:]:
            bakeoff(model, os.environ["GOLDEN_S3_PREFIX"])
