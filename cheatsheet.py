"""Output a layered EuroSCORE II cheatsheet (MDCalc style) for a patient.

Usage:
    python cheatsheet.py <patient_yaml_path>

Patient YAML looks like:
    chart: "XXXXXXXX"
    name: "XXX"
    age: 69
    female: false
    weight_kg: 52.7
    cr_mg_dl: 1.22
    egfr: 65          # optional; if present, used to classify renal
    nyha: I           # default
    ccs4: true        # default Y for CAD post PCI per project rule
    iddm: false
    extracardiac_arteriopathy: false
    chronic_pulmonary_disease: false
    poor_mobility: false
    previous_cardiac_surgery: false
    active_endocarditis: false
    critical_preop: false
    lv_function: good   # leave at good if no echo
    recent_mi: false
    pa_systolic: none
    urgency: elective
    weight_of_procedure: isolated_cabg
    thoracic_aorta: false
    manual_score: 0.0087   # optional, for diff comparison
"""
import sys, io, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import yaml
from euroscore_ii import calc, cockcroft_gault, renal_category

RENAL_LABEL = {
    "normal": "Normal (CC > 85)",
    "cc_50_85": "Moderate (50 < CC < 85)",
    "cc_le_50": "Severe (CC < 50)",
    "dialysis": "Dialysis",
}
LV_LABEL = {
    "good": "Good (LVEF > 50%)",
    "moderate": "Moderate (LVEF 31%-50%)",
    "poor": "Poor (LVEF 21%-30%)",
    "very_poor": "Very poor (LVEF < 20%)",
}
PA_LABEL = {
    "none": "No (PASP < 31)",
    "31_55": "Moderate (PASP 31~55 mmHg)",
    "ge_55": "Severe (PASP > 55 mmHg)",
}
NYHA_LABEL = {"I": "I", "II": "II", "III": "III", "IV": "IV"}
URGENCY_LABEL = {"elective": "Elective", "urgent": "Urgent",
                 "emergency": "Emergency", "salvage": "Salvage"}
WEIGHT_LABEL = {
    "isolated_cabg": "Isolated CABG",
    "single_non_cabg": "Single non-CABG",
    "two": "2 procedures",
    "three_plus": "3 procedures",
}


def yn(v):
    return "Yes" if v else "No"


def render(p):
    # Compute CC if not provided
    cc_calc = cockcroft_gault(p.get("age"), p.get("weight_kg"),
                              p.get("cr_mg_dl"), p.get("female", False))
    egfr = p.get("egfr")
    # Renal classification: ALWAYS use Cockcroft-Gault (EuroSCORE II official)
    # eGFR is informational only.
    if p.get("renal") == "dialysis":
        renal = "dialysis"
    elif cc_calc is not None:
        renal = renal_category(cc_calc)
    else:
        renal = p.get("renal") or "normal"
    p["renal"] = renal

    score = calc(p)
    pct = score * 100

    out = []
    out.append("=" * 70)
    out.append(f"【{p['name']}】病歷號 {p['chart']}")
    if "admit" in p:
        out.append(f"  入院 {p.get('admit','?')} → 出院 {p.get('dc','?')}")
    out.append("=" * 70)

    out.append("Patient related factors")
    out.append(f"  Age:                       {p['age']}")
    out.append(f"  Gender:                    {'Female' if p.get('female') else 'Male'}")
    if p.get("weight_kg") and p.get("cr_mg_dl"):
        cc_txt = f"CG={cc_calc:.1f}"
        if egfr is not None:
            cc_txt += f", eGFR={egfr}"
        out.append(f"  (CC reference:             {cc_txt})")
    out.append(f"  Renal impairment:          {RENAL_LABEL[renal]}")
    out.append(f"  Extracardiac arteriopathy: {yn(p.get('extracardiac_arteriopathy'))}")
    out.append(f"  Poor mobility:             {yn(p.get('poor_mobility'))}")
    out.append(f"  Previous cardiac surgery:  {yn(p.get('previous_cardiac_surgery'))}")
    out.append(f"  Chronic lung disease:      {yn(p.get('chronic_pulmonary_disease'))}")
    out.append(f"  Active endocarditis:       {yn(p.get('active_endocarditis'))}")
    out.append(f"  Critical preoperative:     {yn(p.get('critical_preop'))}")
    out.append(f"  Diabetes on insulin:       {yn(p.get('iddm'))}")

    out.append("Cardiac related factors")
    out.append(f"  NYHA:                      {NYHA_LABEL.get(p.get('nyha','I'),'I')}")
    out.append(f"  CCS class 4 angina:        {yn(p.get('ccs4'))}")
    out.append(f"  LV function:               {LV_LABEL[p.get('lv_function','good')]}")
    out.append(f"  Recent MI:                 {yn(p.get('recent_mi'))}")
    out.append(f"  Pulmonary hypertension:    {PA_LABEL[p.get('pa_systolic','none')]}")

    out.append("Operation related factors")
    out.append(f"  Urgency:                   {URGENCY_LABEL[p.get('urgency','elective')]}")
    out.append(f"  Weight of intervention:    {WEIGHT_LABEL[p.get('weight_of_procedure','isolated_cabg')]}")
    out.append(f"  Surgery on thoracic aorta: {yn(p.get('thoracic_aorta'))}")

    out.append("-" * 70)
    line = f"  EuroSCORE II:              {pct:.2f}%"
    if "manual_score" in p:
        manual = p["manual_score"] * 100
        diff = pct - manual
        line += f"   (manual: {manual:.2f}%, diff: {diff:+.2f}%)"
    out.append(line)
    out.append("=" * 70)

    return "\n".join(out), score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("yaml_files", nargs="+")
    args = ap.parse_args()
    for path in args.yaml_files:
        with open(path, "r", encoding="utf-8") as f:
            p = yaml.safe_load(f)
        out, score = render(p)
        print(out)
        print()


if __name__ == "__main__":
    main()
