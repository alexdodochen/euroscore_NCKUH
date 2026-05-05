"""Discover medicalsns for a chart via Playwright (Chromium).

The EMR leftFrame tree is JS-driven; raw requests can't trigger it. Playwright
opens a real browser, switches chart in topFrame, waits for leftFrame to refresh,
then extracts all medicalsn anchors with surrounding date/type metadata.

Usage:
    python discover_sns_pw.py <SESSION_ID> <CHART> [<CHART2> ...] \\
        [--start 2026-01-01] [--stop 2026-08-01] [--headed]

Outputs: _emr_raw/<chart>_sns.json  with list of {sn, type, date, text}
"""
import sys, io, json, re, argparse, time
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
OUT = ROOT / "_emr_raw"
OUT.mkdir(exist_ok=True)


def parse_left_html(html):
    """Parse leftFrame HTML for medicalsn anchors.

    Tree rows look like: <li>...<a href="...?type=DC&chartno=X&medicalsn=I123...">
    Discharge Note 2026-04-20 ...</a>...</li>
    """
    rows = []
    # Each <li> usually wraps one entry. Match each anchor with medicalsn.
    for a_match in re.finditer(
        r'<a[^>]*href=["\']([^"\']*medicalsn=([IO]\d+)[^"\']*)["\'][^>]*>([^<]*)</a>',
        html, re.I,
    ):
        href, sn, anchor_text = a_match.group(1), a_match.group(2), a_match.group(3)
        # Type from query: type=DC|AD|PL|diagnosis|soap|order|...
        type_m = re.search(r"type=([a-zA-Z_]+)", href, re.I)
        # Find surrounding <li> for context (date, dept, doctor)
        # Walk back from anchor position
        start = a_match.start()
        li_start = html.rfind("<li", 0, start)
        li_end = html.find("</li>", a_match.end())
        context = html[li_start:li_end] if li_start != -1 and li_end != -1 else anchor_text
        text = re.sub(r"<[^>]+>", " ", context)
        text = re.sub(r"\s+", " ", text).strip()
        # Extract date YYYY-MM-DD or YYYY/MM/DD
        date_m = re.search(r"(20\d{2})[/-](\d{1,2})[/-](\d{1,2})", text)
        rows.append({
            "sn": sn,
            "type": type_m.group(1) if type_m else None,
            "anchor_text": anchor_text.strip(),
            "date": (
                f"{date_m.group(1)}-{int(date_m.group(2)):02d}-{int(date_m.group(3)):02d}"
                if date_m else None
            ),
            "text": text[:300],
        })
    # Dedupe by sn (keep first)
    seen = set()
    uniq = []
    for r in rows:
        if r["sn"] in seen:
            continue
        seen.add(r["sn"])
        uniq.append(r)
    return uniq


def discover(session_id, charts, start_date, stop_date, headed=False):
    base = f"http://hisweb.hosp.ncku/Emrquery/(S({session_id}))/tree/"
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        page.goto(base + "frame.aspx", wait_until="load", timeout=30000)
        # frames: topFrame + leftFrame + mainFrame
        for chart in charts:
            print(f"[{chart}] switching chart...", flush=True)
            top_frame = None
            for fr in page.frames:
                if fr.name == "topFrame":
                    top_frame = fr
                    break
            if top_frame is None:
                print("  ERROR: topFrame not found", flush=True)
                continue
            # Set chart + dates
            top_frame.evaluate(
                """([chart, sd, ed]) => {
                    document.getElementById('txtChartNo').value = chart;
                    if (sd) document.getElementById('StartDate').value = sd;
                    if (ed) document.getElementById('StopDate').value = ed;
                }""",
                [chart, start_date, stop_date],
            )
            # Click BTQuery via Playwright (proper event sequence) and wait for leftFrame nav.
            with page.expect_event("framenavigated", timeout=25000,
                                    predicate=lambda f: f.name == "leftFrame"):
                top_frame.click("#BTQuery")
            # After leftFrame navigated, poll until its content shows OUR chart in chartno= anchors.
            # The previous chart's content may briefly persist; we want chartno=<chart>.
            html = ""
            deadline = time.time() + 25
            chart_re = re.compile(rf"chartno={chart}\b")
            while time.time() < deadline:
                left_frame = next((fr for fr in page.frames if fr.name == "leftFrame"), None)
                if left_frame:
                    try:
                        html = left_frame.content()
                        if chart_re.search(html) and "medicalsn=" in html:
                            break
                    except Exception:
                        pass
                time.sleep(0.5)
            if not chart_re.search(html):
                print(f"  WARN: leftFrame still empty after 25s for chart {chart}", flush=True)
                (OUT / f"{chart}_left.html").write_text(html or "<empty>", encoding="utf-8")
                results[chart] = []
                continue
            (OUT / f"{chart}_left.html").write_text(html, encoding="utf-8")
            rows = parse_left_html(html)
            print(f"  found {len(rows)} sns", flush=True)
            results[chart] = rows
        browser.close()
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("charts", nargs="+")
    ap.add_argument("--start", default="2026-01-01")
    ap.add_argument("--stop", default="2026-08-01")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    res = discover(args.session, args.charts, args.start, args.stop, args.headed)
    for chart, rows in res.items():
        out_path = OUT / f"{chart}_sns.json"
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"\n=== {chart} ===")
        i_rows = [r for r in rows if r["sn"].startswith("I")]
        o_rows = [r for r in rows if r["sn"].startswith("O")]
        print(f"  saved → {out_path.name}  (I={len(i_rows)} O={len(o_rows)})")
        for r in i_rows:
            print(f"    [I] {r['sn']:14s} {r.get('date') or '?':10s} {r.get('type') or '?':10s} {r['anchor_text'][:50]}")


if __name__ == "__main__":
    main()
