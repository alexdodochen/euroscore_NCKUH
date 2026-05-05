"""Fetch EMR docs via Playwright while keeping chart active in browser session.

Stand-in for fetch_patient.py when raw `requests` calls hit
IndexOutOfRangeException because the cookieless ASP.NET session needs the
chart switched via top.aspx BTQuery first.

Workflow per chart:
  1. Switch chart in topFrame (txtChartNo + click BTQuery)
  2. Wait leftFrame to refresh with chartno=<chart>
  3. For each (sn, doctype) the user passes, navigate mainFrame to the viewer
     URL, capture body text
  4. Concatenate to _emr_raw/<chart>_raw.txt

Usage:
    python fetch_via_pw.py <SESSION_ID> <CHART:I_SN[,O_SN1,O_SN2,...]> ...

Example:
    python fetch_via_pw.py SID 10921608:I20260016298,O20220221006789
"""
import sys, io, time, argparse, re
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
OUT = ROOT / "_emr_raw"
OUT.mkdir(exist_ok=True)

INPATIENT_DOCS_DISCHARGED = [
    ("DC", "viewer_v2"), ("AD", "viewer_v2"), ("PL", "viewer_v2"),
    ("diagnosis", "viewer"), ("order", "viewer"), ("consult", "viewer"),
]
INPATIENT_DOCS_ACTIVE = [
    ("AD", "iviewer"), ("PL", "iviewer"),
    ("diagnosis", "iviewer"), ("order", "iviewer"), ("consult", "iviewer"),
    ("DRG", "viewer_v2"),
]
OUTPATIENT_DOCS = [("diagnosis", "viewer"), ("soap", "viewer"),
                    ("order", "viewer")]


def detect_inpatient_active(left_html, chart, sn):
    """True if leftFrame uses iviewer.aspx for this exact (chart, sn) pair."""
    if not left_html:
        return False
    h = left_html.replace("&amp;", "&")
    # Look for the full pattern with our chart + sn
    return f"iviewer.aspx?type=AD&chartno={chart}&medicalsn={sn}" in h


def html_to_text(html):
    txt = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    txt = re.sub(r"<style.*?</style>", " ", txt, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def switch_chart(page, top_frame, chart, start, stop):
    top_frame.evaluate(
        """([chart, sd, ed]) => {
            document.getElementById('txtChartNo').value = chart;
            if (sd) document.getElementById('StartDate').value = sd;
            if (ed) document.getElementById('StopDate').value = ed;
        }""",
        [chart, start, stop],
    )
    with page.expect_event("framenavigated", timeout=25000,
                           predicate=lambda f: f.name == "leftFrame"):
        top_frame.click("#BTQuery")
    chart_re = re.compile(rf"chartno={chart}\b")
    deadline = time.time() + 25
    while time.time() < deadline:
        left = next((f for f in page.frames if f.name == "leftFrame"), None)
        if left:
            try:
                html = left.content()
                if chart_re.search(html):
                    return left
            except Exception:
                pass
        time.sleep(0.4)
    return None


def fetch_doc(doc_page, base, kind, viewer, chart, sn=None):
    """Open viewer URL on a dedicated Playwright page. Returns body text."""
    url = f"{base}{viewer}.aspx?type={kind}&chartno={chart}"
    if sn:
        url += f"&medicalsn={sn}"
    try:
        doc_page.goto(url, wait_until="load", timeout=20000)
        html = doc_page.content()
    except Exception as e:
        return f"[FETCH ERROR: {e}]"
    return html_to_text(html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("specs", nargs="+",
                    help="<chart>:<sn1>,<sn2>,... per patient")
    ap.add_argument("--start", default="2026-01-01")
    ap.add_argument("--stop", default="2026-08-01")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    base = f"http://hisweb.hosp.ncku/Emrquery/(S({args.session}))/tree/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        page.goto(base + "frame.aspx", wait_until="load", timeout=30000)
        # Dedicated page for fetching viewer docs
        doc_page = ctx.new_page()

        for spec in args.specs:
            chart, _, sn_csv = spec.partition(":")
            sns = [s.strip() for s in sn_csv.split(",") if s.strip()]
            print(f"\n[{chart}] switching chart with {len(sns)} sns...")
            top = next((f for f in page.frames if f.name == "topFrame"), None)
            if top is None:
                print("  ERROR: no topFrame")
                continue
            left = switch_chart(page, top, chart, args.start, args.stop)
            if left is None:
                print(f"  WARN: leftFrame did not refresh for {chart}, continuing anyway")
            sections = []
            left_html = left.content() if left else ""
            for sn in sns:
                if sn.upper().startswith("I"):
                    label = "住院"
                    if detect_inpatient_active(left_html, chart, sn):
                        docs = INPATIENT_DOCS_ACTIVE
                        print(f"    (sn={sn} → active admission, using iviewer)")
                    else:
                        docs = INPATIENT_DOCS_DISCHARGED
                        print(f"    (sn={sn} → discharged, using viewer/viewer_v2)")
                else:
                    label = "門診"
                    docs = OUTPATIENT_DOCS
                for kind, viewer in docs:
                    txt = fetch_doc(doc_page, base, kind, viewer, chart, sn) or ""
                    sections.append(f"=== [{label}] {kind} (sn={sn}) ===\n{txt}")
                    print(f"    [{label}] {kind:10s} ({sn}): {len(txt)} chars")
            # owhbchemo (chart-wide)
            txt = fetch_doc(doc_page, base, "owhbchemo", "viewer_v2", chart) or ""
            sections.append(f"=== owhbchemo (chart-wide) ===\n{txt}")
            print(f"    owhbchemo: {len(txt)} chars")

            raw_path = OUT / f"{chart}_raw.txt"
            raw_path.write_text("\n\n".join(sections), encoding="utf-8")
            print(f"  → saved {raw_path.name}")
        browser.close()


if __name__ == "__main__":
    main()
