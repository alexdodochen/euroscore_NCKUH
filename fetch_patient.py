"""Fetch a patient's EMR docs via Python requests using EMR session URL.

Usage: python fetch_patient.py <SESSION_ID> <chart> [<sn>]

If sn omitted, fetches owhbchemo only (chart-wide doc).
Saves to _emr_raw/<chart>_raw.txt with sections separated by ===.
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
    ap.add_argument("sn", nargs="?", default=None)
    args = ap.parse_args()

    base = f"http://hisweb.hosp.ncku/Emrquery/(S({args.session}))/tree/"
    out_dir = Path(__file__).parent / "_emr_raw"
    out_dir.mkdir(exist_ok=True)

    sections = []
    if args.sn:
        for kind, viewer in [("DC", "viewer_v2"), ("AD", "viewer_v2"),
                              ("PL", "viewer_v2"), ("diagnosis", "viewer"),
                              ("order", "viewer")]:
            try:
                txt = fetch(base, kind, args.chart, args.sn, viewer)
                sections.append(f"=== {kind} (sn={args.sn}) ===\n{txt}")
                print(f"  fetched {kind}: {len(txt)} chars")
            except Exception as e:
                print(f"  ERROR {kind}: {e}")

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
