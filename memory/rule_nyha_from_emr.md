---
name: euroscore-nyha-evaluate-from-emr
description: Never default NYHA to I. Read AD/DC for symptom history (DOE/orthopnea/PND/effort tolerance) and assign NYHA class clinically. Always document rationale.
type: rule
---

**Rule:** Evaluate `nyha` from EMR symptom history. Do NOT default to I just because no formal NYHA grade is documented in the AD.

**Why:** Defaulting NYHA to I systematically under-scores most cardiac admission patients. Most cardiac admissions have effort-related symptoms documented in the Present Illness section (DOE, exertional chest tightness, walking-induced symptoms) that map cleanly to NYHA II or III.

**How to apply:**
- Read AD's Present Illness + Past History + ROS (especially CV system: DOE / orthopnea / PND / pedal edema / chest tightness on effort).
- Map symptoms to NYHA:
  - **I** — no symptoms with ordinary activity (baseline AD says "no DOE, no orthopnea, ADL independent without complaints")
  - **II** — slight limitation; ordinary activity (walking, climbing stairs) causes effort symptoms; comfortable at rest
  - **III** — marked limitation; less than ordinary activity causes symptoms; comfortable at rest
  - **IV** — symptoms at rest
- For acute admissions (NSTEMI / STEMI / IABP), use the **baseline preop functional state** (recent weeks pre-admission), NOT the current acute decompensation. `critical_preop` already captures acute deterioration; do not double-count by inflating NYHA.
- If AD documents effort-related chest tightness or dyspnea over weeks–months → at minimum NYHA II.
- Always include rationale citing the specific AD/DC quote.

**Example:** AD says "intermittent chest tightness, dizziness, cold sweating ... precipitated while walking, 1–2 months" → NYHA II (walking = ordinary activity).
