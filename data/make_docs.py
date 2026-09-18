"""Fixture JSON -> printable HTML + expected extraction JSON.

Usage: python data/make_docs.py
Then open each data/out/*.html, print to PDF or paper, and photograph it.

Optional fixture fields (unknown fields such as printNote are ignored):
  layout          "table" (default) | "freetext" (numbered lines, no table) | "opd" (prescription pad)
  hospitalLocal   extra header line, e.g. the hospital name in Kannada
  doctor          signature block HTML (default: the case01 cardiologist)
  pageBreakAfter  split the medicine table onto a new printed page after this many rows
  visitDate       used by the opd layout instead of admitted/discharged
"""
import glob
import json
import os

from api.frequency import parse_frequency

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "out")
GOLDEN = os.path.join(HERE, "golden")
DEFAULT_DOCTOR = "Dr. S. Patil, MD DM (Cardiology)<br>Reg. No. KMC/48213"

HTML = """<!doctype html><meta charset="utf-8"><title>{caseId}</title>
<style>
 body {{ font-family: Georgia, serif; margin: 28px; font-size: 13px; color:#000 }}
 h1 {{ font-size: 16px; text-align:center; margin:0 0 2px }}
 .sub {{ text-align:center; font-size:11px; margin-bottom:14px }}
 table {{ border-collapse: collapse; width: 100%; margin: 10px 0 }}
 th, td {{ border: 1px solid #333; padding: 5px 7px; text-align: left; font-size: 12px }}
 .row {{ display:flex; gap:26px; margin-bottom:4px }}
 .box {{ border:1px solid #333; padding:8px; margin-top:10px }}
</style>
{local}<h1>{hospital}</h1>
<div class="sub">DISCHARGE SUMMARY</div>
<div class="row"><div><b>Name:</b> {name}</div><div><b>Age/Sex:</b> {age}/{sex}</div>
<div><b>UHID:</b> {uhid}</div></div>
<div class="row"><div><b>Date of Admission:</b> {admitted}</div>
<div><b>Date of Discharge:</b> {discharged}</div></div>
<div><b>Final Diagnosis:</b> {diagnosis}</div>
{meds}
<div class="box"><b>Warning signs — report immediately if:</b><br>{redflags}</div>
<div class="box"><b>Follow up:</b> {followup}</div>
<div style="margin-top:22px">Discharged in stable condition.<br><br>
{doctor}</div>
"""

OPD = """<!doctype html><meta charset="utf-8"><title>{caseId}</title>
<style>
 body {{ font-family: Arial, sans-serif; margin: 28px; font-size: 13px; color:#000 }}
 .head {{ border-bottom: 2px solid #000; padding-bottom: 6px; margin-bottom: 10px }}
 .row {{ display:flex; gap:26px; margin-bottom:4px }}
 .rx {{ font-family: Georgia, serif; font-size: 30px; margin: 12px 0 0 }}
 ol li {{ margin: 7px 0 }}
</style>
<div class="head"><b style="font-size:17px">{doctor}</b><br>{hospital}</div>
<div class="row"><div><b>Name:</b> {name}</div><div><b>Age/Sex:</b> {age}/{sex}</div>
<div><b>OP No:</b> {uhid}</div><div><b>Date:</b> {visitDate}</div></div>
<div><b>Dx:</b> {diagnosis}</div>
<div class="rx">&#8478;</div>
<ol>{meds}</ol>
<div><b>Come back immediately if:</b> {redflags}</div>
<div style="margin-top:6px"><b>Review:</b> {followup}</div>
<div style="margin-top:34px;text-align:right">Signature</div>
"""


def expected(fixture):
    meds = []
    for i, m in enumerate(fixture["medicines"], start=1):
        slots, prn = parse_frequency(m["frequency"])
        meds.append({
            "lineId": "m%d" % i, "brand": m["brand"], "molecules": m["molecules"],
            "frequency": m["frequency"], "slots": slots, "prn": prn,
            "prnCondition": m.get("prnCondition"),
            "foodRelation": m["foodRelation"], "durationDays": m["durationDays"],
        })
    return {"caseId": fixture["caseId"], "medicines": meds,
            "redFlags": {"source": "document", "text": fixture["redFlags"]},
            "followUp": fixture["followUp"]}


def med_block(fx):
    raws = [m["raw"] for m in fx["medicines"]]
    layout = fx.get("layout", "table")
    if layout == "opd":
        return "".join("<li>%s</li>" % r for r in raws)
    if layout == "freetext":
        return "<p><b>Advice on discharge:</b><br>%s</p>" % "<br>".join(
            "%d) %s" % (i, r) for i, r in enumerate(raws, start=1))
    rows = ["<tr><td>%d</td><td>%s</td></tr>" % (i, r) for i, r in enumerate(raws, start=1)]
    head = "<table><tr><th>#</th><th>Medication advised on discharge%s</th></tr>"
    split = fx.get("pageBreakAfter") or len(rows)
    html = head % "" + "".join(rows[:split]) + "</table>"
    if rows[split:]:
        html += ('<div style="break-after:page"></div>' + head % " (contd.)"
                 + "".join(rows[split:]) + "</table>")
    return html


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(GOLDEN, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(HERE, "fixtures", "*.json"))):
        fx = json.load(open(path, encoding="utf-8"))
        local = fx.get("hospitalLocal")
        html = (OPD if fx.get("layout") == "opd" else HTML).format(
            caseId=fx["caseId"], hospital=fx["hospital"],
            local='<h1>%s</h1>\n' % local if local else "",
            name=fx["patient"]["name"], age=fx["patient"]["age"],
            sex=fx["patient"]["sex"], uhid=fx["patient"]["uhid"],
            admitted=fx.get("admitted"), discharged=fx.get("discharged"),
            visitDate=fx.get("visitDate"), diagnosis=fx["diagnosis"], meds=med_block(fx),
            redflags=fx["redFlags"], doctor=fx.get("doctor", DEFAULT_DOCTOR),
            followup="%s with %s" % (fx["followUp"]["date"], fx["followUp"]["with"]))
        open(os.path.join(OUT, fx["caseId"] + ".html"), "w", encoding="utf-8").write(html)
        json.dump(expected(fx), open(os.path.join(GOLDEN, fx["caseId"] + ".json"), "w",
                                     encoding="utf-8"), indent=2, ensure_ascii=False)
        print("wrote", fx["caseId"])


if __name__ == "__main__":
    main()
