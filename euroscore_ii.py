"""EuroSCORE II calculator.

Source: Nashef SAM et al. EuroSCORE II. Eur J Cardiothorac Surg 2012;41:734-745.
Coefficients from Table 6 of the original paper.

Usage:
    inputs = {
        "age": 70, "female": False,
        "nyha": "II",
        "ccs4": False, "iddm": False,
        "extracardiac_arteriopathy": False,
        "chronic_pulmonary_disease": False,
        "poor_mobility": False,
        "previous_cardiac_surgery": False,
        "renal": "normal",         # normal | cc_50_85 | cc_le_50 | dialysis
        "active_endocarditis": False,
        "critical_preop": False,
        "lv_function": "good",     # good | moderate | poor | very_poor
        "recent_mi": False,
        "pa_systolic": "none",     # none | 31_55 | ge_55
        "urgency": "elective",     # elective | urgent | emergency | salvage
        "weight_of_procedure": "isolated_cabg",
                                   # isolated_cabg | single_non_cabg | two | three_plus
        "thoracic_aorta": False,
    }
    score = calc(inputs)   # returns float in 0..1 (predicted mortality)
"""
from math import exp

CONSTANT = -5.324537

BETA = {
    "age": 0.0285181,
    "female": 0.2196434,
    # NYHA
    "nyha_ii": 0.1070545,
    "nyha_iii": 0.2958358,
    "nyha_iv": 0.5597929,
    "ccs4": 0.2226147,
    "iddm": 0.3542749,
    "extracardiac_arteriopathy": 0.5360268,
    "chronic_pulmonary_disease": 0.1886564,
    "poor_mobility": 0.2407181,
    "previous_cardiac_surgery": 1.118599,
    # Renal
    "dialysis": 0.6421508,
    "cc_le_50": 0.8592256,
    "cc_50_85": 0.303553,
    "active_endocarditis": 0.6194522,
    "critical_preop": 1.086517,
    # LV
    "lv_moderate": 0.3150652,
    "lv_poor": 0.8084096,
    "lv_very_poor": 0.9346919,
    "recent_mi": 0.1528943,
    # PA pressure
    "pa_31_55": 0.1788899,
    "pa_ge_55": 0.3491475,
    # Urgency
    "urgent": 0.3174673,
    "emergency": 0.7039121,
    "salvage": 1.362947,
    # Weight of procedure
    "single_non_cabg": 0.0062118,
    "two": 0.5521478,
    "three_plus": 0.9724533,
    "thoracic_aorta": 0.6527205,
}


def age_x(age):
    """Age coding: Xi=1 if age<=60; +1 per year above 60."""
    if age is None:
        return 0
    if age <= 60:
        return 1
    return 1 + (age - 60)


def calc(d):
    """Compute predicted mortality (0..1). Missing keys are treated as 'no'."""
    y = CONSTANT
    y += BETA["age"] * age_x(d.get("age"))
    if d.get("female"):
        y += BETA["female"]

    nyha = (d.get("nyha") or "").upper()
    if nyha == "II":
        y += BETA["nyha_ii"]
    elif nyha == "III":
        y += BETA["nyha_iii"]
    elif nyha == "IV":
        y += BETA["nyha_iv"]

    for k in ("ccs4", "iddm", "extracardiac_arteriopathy",
              "chronic_pulmonary_disease", "poor_mobility",
              "previous_cardiac_surgery", "active_endocarditis",
              "critical_preop", "recent_mi", "thoracic_aorta"):
        if d.get(k):
            y += BETA[k]

    renal = d.get("renal") or "normal"
    if renal == "dialysis":
        y += BETA["dialysis"]
    elif renal == "cc_le_50":
        y += BETA["cc_le_50"]
    elif renal == "cc_50_85":
        y += BETA["cc_50_85"]

    lv = d.get("lv_function") or "good"
    if lv == "moderate":
        y += BETA["lv_moderate"]
    elif lv == "poor":
        y += BETA["lv_poor"]
    elif lv == "very_poor":
        y += BETA["lv_very_poor"]

    pa = d.get("pa_systolic") or "none"
    if pa == "31_55":
        y += BETA["pa_31_55"]
    elif pa == "ge_55":
        y += BETA["pa_ge_55"]

    urg = d.get("urgency") or "elective"
    if urg == "urgent":
        y += BETA["urgent"]
    elif urg == "emergency":
        y += BETA["emergency"]
    elif urg == "salvage":
        y += BETA["salvage"]

    w = d.get("weight_of_procedure") or "isolated_cabg"
    if w == "single_non_cabg":
        y += BETA["single_non_cabg"]
    elif w == "two":
        y += BETA["two"]
    elif w == "three_plus":
        y += BETA["three_plus"]

    return exp(y) / (1 + exp(y))


def cockcroft_gault(age, weight_kg, cr_mg_dl, female):
    """Estimate creatinine clearance (ml/min)."""
    if not (age and weight_kg and cr_mg_dl):
        return None
    factor = 0.85 if female else 1.0
    return (140 - age) * weight_kg * factor / (72 * cr_mg_dl)


def renal_category(cc):
    if cc is None:
        return "normal"
    if cc > 85:
        return "normal"
    if cc >= 50:
        return "cc_50_85"
    return "cc_le_50"


if __name__ == "__main__":
    # Sanity check: 65yo male, elective isolated CABG, otherwise healthy
    baseline = calc({"age": 65, "urgency": "elective",
                     "weight_of_procedure": "isolated_cabg"})
    print(f"65yo male elective CABG baseline: {baseline*100:.2f}%")

    # High risk: 80yo female, NYHA IV, critical preop, redo, CC<50, emergency, 2 procedures
    hi = calc({
        "age": 80, "female": True, "nyha": "IV",
        "previous_cardiac_surgery": True, "critical_preop": True,
        "renal": "cc_le_50", "lv_function": "poor",
        "urgency": "emergency", "weight_of_procedure": "two",
    })
    print(f"High-risk example: {hi*100:.2f}%")
