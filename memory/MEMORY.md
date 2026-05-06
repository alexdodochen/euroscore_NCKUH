# Memory index — EuroSCORE project

This file is the index for memory entries. All tracked memory in this PUBLIC repo must be PHI-safe — generalizable methodology and scoring rules only. Patient-specific data lives in `_emr_raw/` (gitignored) and chat.

- [HANDOFF](HANDOFF.md) — current session handoff (overwritten each `/workflow-docs` run)
- [rule-iddm-in-hospital-insulin](rule_iddm_in_hospital_insulin.md) — IDDM = Y if any insulin in inpatient order list
- [rule-age-calendar-year](rule_age_calendar_year.md) — Age = admission_year − birth_year (ignore EMR-displayed age)
- [rule-nyha-from-emr](rule_nyha_from_emr.md) — NYHA must be evaluated from EMR symptom history (never default to I)
