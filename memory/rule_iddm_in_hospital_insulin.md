---
name: euroscore-iddm-in-hospital-insulin
description: For EuroSCORE II IDDM field, count Y whenever ANY insulin appears in the inpatient order list — do NOT require chronic preop insulin.
type: rule
---

**Rule:** `iddm = Y` if the inpatient order list contains any insulin during this admission, regardless of whether the patient was on chronic insulin preoperatively. Even sliding-scale Insulin Regular (Humulin R) for stress hyperglycemia in CCU counts as Y.

**Why:** Order-based classification is easier, less subjective, and matches the `gemini_prompt.md` schema literal ("iddm: true ONLY if Order list mentions insulin/..."). The strict "preop chronic insulin only" interpretation systematically under-scored ICU patients with stress hyperglycemia.

**How to apply:**
- Grep the order list for: insulin / Humulin / Lantus / Toujeo / Tresiba / NovoMix / NovoRapid / Aspart / Glargine / Levemir / NPH / Apidra / Ryzodeg / Actrapid.
- Any hit → `iddm: true`. Rationale should cite the drug + start date + indication (chronic vs sliding scale OK to note, but doesn't change the verdict).
- Outpatient-only insulin or no insulin → `iddm: false`.
- Applies even when the home meds were oral hypoglycemics only and insulin started in-hospital.
