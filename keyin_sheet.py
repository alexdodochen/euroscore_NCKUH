"""Print key-in tables in MDCalc field order.

For each YAML in _emr_raw/, output a table the user can copy directly into
the hospital MDCalc-style EuroSCORE II form:

    Field                     | Value          | β coefficient
    Age                       | 72             | 0.0285181
    Gender                    | Male           | 0
    Renal impairment          | Severe (CC<50) | 0.8592256
    ...
    EuroSCORE II              | 10.10%
"""
import sys, io
from pathlib import Path
import yaml
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from euroscore_ii import calc, cockcroft_gault, renal_category, BETA, age_x

ROOT = Path(__file__).parent

# (label, value_fn, beta_fn) — order matches MDCalc UI screenshot exactly
FIELDS_PATIENT = [
    ("Age", lambda p: str(p.get("age")),
        lambda p: BETA["age"] * age_x(p.get("age"))),
    ("Gender", lambda p: "Female" if p.get("female") else "Male",
        lambda p: BETA["female"] if p.get("female") else 0.0),
    ("Renal impairment", lambda p: {
            "normal": "Normal (CC>85)",
            "cc_50_85": "Moderate (CC 50-85)",
            "cc_le_50": "Severe (CC<50)",
            "dialysis": "Dialysis",
        }.get(p.get("renal", "normal"), p.get("renal")),
        lambda p: {
            "dialysis": BETA["dialysis"],
            "cc_le_50": BETA["cc_le_50"],
            "cc_50_85": BETA["cc_50_85"],
        }.get(p.get("renal", "normal"), 0.0)),
    ("Extracardiac arteriopathy", lambda p: "Y" if p.get("extracardiac_arteriopathy") else "N",
        lambda p: BETA["extracardiac_arteriopathy"] if p.get("extracardiac_arteriopathy") else 0.0),
    ("Poor mobility", lambda p: "Y" if p.get("poor_mobility") else "N",
        lambda p: BETA["poor_mobility"] if p.get("poor_mobility") else 0.0),
    ("Previous cardiac surgery", lambda p: "Y" if p.get("previous_cardiac_surgery") else "N",
        lambda p: BETA["previous_cardiac_surgery"] if p.get("previous_cardiac_surgery") else 0.0),
    ("Chronic lung disease", lambda p: "Y" if p.get("chronic_pulmonary_disease") else "N",
        lambda p: BETA["chronic_pulmonary_disease"] if p.get("chronic_pulmonary_disease") else 0.0),
    ("Active endocarditis", lambda p: "Y" if p.get("active_endocarditis") else "N",
        lambda p: BETA["active_endocarditis"] if p.get("active_endocarditis") else 0.0),
    ("Critical preoperative state", lambda p: "Y" if p.get("critical_preop") else "N",
        lambda p: BETA["critical_preop"] if p.get("critical_preop") else 0.0),
    ("Diabetes on insulin", lambda p: "Y" if p.get("iddm") else "N",
        lambda p: BETA["iddm"] if p.get("iddm") else 0.0),
]

FIELDS_CARDIAC = [
    ("NYHA", lambda p: p.get("nyha", "I"),
        lambda p: {"II": BETA["nyha_ii"], "III": BETA["nyha_iii"], "IV": BETA["nyha_iv"]}.get((p.get("nyha") or "I").upper(), 0.0)),
    ("CCS class 4 angina", lambda p: "Y" if p.get("ccs4") else "N",
        lambda p: BETA["ccs4"] if p.get("ccs4") else 0.0),
    ("LV function", lambda p: {
            "good": "Good (>50%)",
            "moderate": "Moderate (31-50%)",
            "poor": "Poor (21-30%)",
            "very_poor": "Very poor (≤20%)",
        }.get(p.get("lv_function", "good"), "Good"),
        lambda p: {"moderate": BETA["lv_moderate"], "poor": BETA["lv_poor"],
                    "very_poor": BETA["lv_very_poor"]}.get(p.get("lv_function", "good"), 0.0)),
    ("Recent MI", lambda p: "Y" if p.get("recent_mi") else "N",
        lambda p: BETA["recent_mi"] if p.get("recent_mi") else 0.0),
    ("Pulmonary hypertension", lambda p: {
            "none": "No (PASP<31)",
            "31_55": "Moderate (31-55)",
            "ge_55": "Severe (>55)",
        }.get(p.get("pa_systolic", "none"), "No"),
        lambda p: {"31_55": BETA["pa_31_55"], "ge_55": BETA["pa_ge_55"]}.get(p.get("pa_systolic", "none"), 0.0)),
]

FIELDS_OPERATION = [
    ("Urgency", lambda p: {
            "elective": "Elective", "urgent": "Urgent",
            "emergency": "Emergency", "salvage": "Salvage",
        }.get(p.get("urgency", "elective"), "Elective"),
        lambda p: {"urgent": BETA["urgent"], "emergency": BETA["emergency"],
                    "salvage": BETA["salvage"]}.get(p.get("urgency", "elective"), 0.0)),
    ("Weight of the intervention", lambda p: {
            "isolated_cabg": "Isolated CABG",
            "single_non_cabg": "Single non-CABG",
            "two": "2 procedures",
            "three_plus": "3+ procedures",
        }.get(p.get("weight_of_procedure", "isolated_cabg"), "Isolated CABG"),
        lambda p: {"single_non_cabg": BETA["single_non_cabg"], "two": BETA["two"],
                    "three_plus": BETA["three_plus"]}.get(p.get("weight_of_procedure", "isolated_cabg"), 0.0)),
    ("Surgery on thoracic aorta", lambda p: "Y" if p.get("thoracic_aorta") else "N",
        lambda p: BETA["thoracic_aorta"] if p.get("thoracic_aorta") else 0.0),
]


def fmt_beta(b):
    if b == 0:
        return "0"
    return f"{b:.7f}".rstrip("0").rstrip(".")


def render(p):
    # Apply renal classification (cheatsheet auto-computes)
    cc = cockcroft_gault(p.get("age"), p.get("weight_kg"),
                          p.get("cr_mg_dl"), p.get("female", False))
    if p.get("renal") == "dialysis":
        pass
    elif cc is not None:
        p["renal"] = renal_category(cc)
    score = calc(p)
    pct = score * 100

    out = []
    out.append("=" * 72)
    out.append(f"【{p['name']}】病歷號 {p['chart']}    入院 {p.get('admit','?')} → {p.get('dc','?')}")
    out.append("=" * 72)

    def section(title, fields):
        out.append(f"┌── {title} ──")
        for label, vf, bf in fields:
            v = vf(p)
            b = bf(p)
            out.append(f"│  {label:30s}  {v:24s}  {fmt_beta(b)}")

    section("Patient related factors", FIELDS_PATIENT)
    section("Cardiac related factors", FIELDS_CARDIAC)
    section("Operation related factors", FIELDS_OPERATION)
    out.append("└" + "─" * 71)
    out.append(f"   EuroSCORE II:   {pct:.2f}%")
    out.append("=" * 72)
    return "\n".join(out)


def main():
    yamls = sorted((ROOT / "_emr_raw").glob("*.yaml"))
    for yp in yamls:
        with open(yp, "r", encoding="utf-8") as f:
            p = yaml.safe_load(f)
        print(render(p))
        print()


if __name__ == "__main__":
    main()
