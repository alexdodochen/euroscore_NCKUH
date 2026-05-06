---
name: euroscore-age-calendar-year-subtraction
description: For EuroSCORE II Age field, ALWAYS use admission_year − birth_year (calendar-year subtraction). Do NOT use the EMR AD-displayed age, which subtracts months.
type: rule
---

**Rule:** `age = admission_year − birth_year` (calendar-year subtraction). Ignore months and days. This matches the original EuroSCORE II convention and the MDCalc form.

**Why:** EMR Admission Notes display age as "true age" (subtracts months for birthdays not yet reached this year). EuroSCORE II uses calendar-year subtraction, which can be one year higher than the AD-displayed age. Each off-by-one year shifts the logit by `0.0285181`, producing a small but consistent under-scoring drift if the AD age is used.

**How to apply:**
- Read the patient's DOB and admission date from AD.
- Compute `age = admission_year − birth_year`. Ignore the AD's "Age:" field if it differs.
- Example: born 1953/08, admitted 2026/04 → AD shows Age 72 (birthday in August not yet reached), but EuroSCORE age = 2026 − 1953 = **73**.

This is also documented in the skill body (rule #1) and the project README. Stay disciplined; do not drift to AD-displayed age.
