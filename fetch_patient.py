"""Fetch a patient's EMR docs via Python requests using EMR session URL.

Usage:
    python fetch_patient.py <SESSION_ID> <chart> [<sn1> <sn2> ...]

  sns can be inpatient (I20...) or outpatient (O20...).
  - I-prefix → fetch DC, AD, PL, diagnosis, order
  - O-prefix → fetch diagnosis, soap, order (門診紀錄)
  Always fetches owhbchemo (chart-wide).

For ECA/CPD/IDDM 等容易漏的診斷，建議帶上住院前後 ±3 個月的 OPD sns 一起掃。
"""
import sys, io, argparse, requests
from pathlib import Path
from html.parser import HTMLParser

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = False

    def handle_data(self, data):
        if not self.skip:
            self.text_parts.append(data)


def html_to_text(html):
    p = TextExtractor()
    p.feed(html)
    txt = " ".join(p.text_parts)
    # collapse whitespace
    return " ".join(txt.split())


def fetch(base, kind, chart, sn=None, viewer="viewer_v2"):
    url = f"{base}{viewer}.aspx?type={kind}&chartno={chart}"
    if sn:
        url += f"&medicalsn={sn}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return html_to_text(r.text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session", help="EMR session ID (the part inside (S(...)))")
    ap.add_argument("chart")
    ap.add_argument("sns", nargs="*", default=[],
                    help="One or more medical sns. I-prefix=inpatient, O-prefix=outpatient.")
    args = ap.parse_args()

    base = f"http://hisweb.hosp.ncku/Emrquery/(S({args.session}))/tree/"
    out_dir = Path(__file__).parent / "_emr_raw"
    out_dir.mkdir(exist_ok=True)

    INPATIENT_DOCS = [("DC", "viewer_v2"), ("AD", "viewer_v2"),
                       ("PL", "viewer_v2"), ("diagnosis", "viewer"),
                       ("order", "viewer")]
    OUTPATIENT_DOCS = [("diagnosis", "viewer"), ("soap", "viewer"),
                        ("order", "viewer")]

    sections = []
    for sn in args.sns:
        docs = INPATIENT_DOCS if sn.upper().startswith("I") else OUTPATIENT_DOCS
        label = "住院" if sn.upper().startswith("I") else "門診"
        for kind, viewer in docs:
            try:
                txt = fetch(base, kind, args.chart, sn, viewer)
                sections.append(f"=== [{label}] {kind} (sn={sn}) ===\n{txt}")
                print(f"  fetched [{label}] {kind} ({sn}): {len(txt)} chars")
            except Exception as e:
                print(f"  ERROR {kind} ({sn}): {e}")

    # owhbchemo (chart-wide, no sn)
    try:
        txt = fetch(base, "owhbchemo", args.chart, None, "viewer_v2")
        sections.append(f"=== owhbchemo (chart-wide) ===\n{txt}")
        print(f"  fetched owhbchemo: {len(txt)} chars")
    except Exception as e:
        print(f"  ERROR owhbchemo: {e}")

    raw_path = out_dir / f"{args.chart}_raw.txt"
    raw_path.write_text("\n\n".join(sections), encoding="utf-8")
    print(f"\nSaved to {raw_path}")


if __name__ == "__main__":
    main()
