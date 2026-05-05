============================================
  HANDOFF — Last Updated: 2026-04-26 09:00
============================================

[What this session did]
  1. Computed EuroSCORE II for the first batch of 5 cath patients.
  2. Wrote scores back to the master sheet `2026 (資訊室CAD-3.2)` column J + 5 evaluation blocks in the per-attending sheet.
  3. Diff-checked auto vs manual scoring; aligned 2 cases where manual had data-entry errors.

[Current state]
  - Branch: main, clean before this handoff edit
  - Latest commit: a7de119 — Playwright fallback for SN discovery + active-admission iviewer support
  - Deploy state: N/A (this is a local computation tool, no deployment)

[Next steps]
  - Fetch next batch of 5 cath patients per the workflow below
  - Optionally test the new Playwright fallback path (`discover_sns_pw.py`, `fetch_via_pw.py`) when the requests-based fetcher fails

[Known issues / blockers]
  - None

[Don't repeat these mistakes]
  - Manual scoring sometimes misses prior cardiac surgery — any pericardium-opening procedure counts (e.g. ascending aorta + hemiarch replacement is previous cardiac surgery)
  - Manual scoring sometimes misclassifies renal severity — use Cockcroft-Gault, not eGFR, for grading; HD/ESRD/dialysis terms always map to "dialysis"

[Relevant files]
  - euroscore_ii.py — Nashef 2012 Table 6 coefficients + CG calc + renal_category
  - cheatsheet.py — YAML → MDCalc-style stratified cheatsheet + diff vs manual
  - fetch_patient.py — direct EMR doc fetch via Python requests (no browser, saves tokens)
  - generate_euroscore_sheet.py — builds the Excel evaluation sheet (21 inputs + auto-calc columns)
  - write_to_excel.py — writes YAML-derived score back to master sheet column J + per-block
  - _emr_raw/<chart>.yaml — per-patient input (gitignored, contains PHI)
  - _emr_raw/gemini_prompt.md — schema given to gemini for raw-text parsing
  - discover_sns_pw.py / fetch_via_pw.py / bootstrap_workbook.py / keyin_sheet.py / mdcalc_sheet.py — added 2026-05-05, Playwright fallback path

[Important memory files]
  - MEMORY.md (index)

============================================
  Workflow (per patient, 9 steps)
============================================

1. Browser switch chart (Chrome MCP): set `txtChartNo`, click `BTQuery`, wait for leftFrame body to contain new chart string.
2. Find sn: in leftFrame, locate `Discharge Note(*)` anchor with `medicalsn=I...`. May have multiple — verify in next step.
3. Python fetch (token-efficient):
     `python fetch_patient.py <SESSION_ID> <chart> <sn>`
   Then check first line of `_emr_raw/<chart>_raw.txt` for admission date to confirm correct sn.
4. Gemini parse (delegated grunt work):
     `cat _emr_raw/gemini_prompt.md _emr_raw/<chart>_raw.txt > _emr_raw/_gemini_input.txt`
     `gemini -p "Extract YAML per schema. Use age = admission_year - birth_year." < _emr_raw/_gemini_input.txt`
5. Read AD/DC manually (clinical comorbidity judgment — Claude's job, not gemini's):
   - critical_preop: IABP / ECMO / shock / decomp HF / acute resp failure / inotropes / VT-VF
   - ECA: claudication / carotid >50% stenosis / amputation / prior or planned aortic-limb-carotid intervention (absent pulse alone does NOT count)
   - previous_cardiac_surgery: any pericardium-opening procedure, including ascending aorta + hemiarch replacement
   - recent_mi: acute MI within 90d (unstable angina != MI)
   - poor_mobility: AD describes daily activity; independent -> N
6. Write YAML to `_emr_raw/<chart>.yaml`, including manual_score and rationale per field.
7. Score it: `python cheatsheet.py _emr_raw/<chart>.yaml`
8. Batch write back to Excel at the end: `python write_to_excel.py`
9. Report using the standard summary table format (chart / name / predicted / manual / diff / alignment status + reason). Keep this report in chat only — never commit it to the public repo.

============================================
  Scoring rules
============================================

1. Age = admission_year - birth_year (calendar-year subtraction, matches MDCalc)
2. NYHA: default I (beta=0)
3. Poor mobility: default N. AD "independent" -> N; "partially dependent" etc. -> Y
4. CCS class 4: default N. Only Y if PI explicitly states "unable to perform any activity"
5. Renal — HD/ESRD/dialysis terms -> dialysis; else Cockcroft-Gault:
     CC > 85 -> normal
     CC 50-85 -> moderate
     CC <= 50 -> severe
   eGFR is reference only, not used for grading
6. No echo: LV=good, PHT=none
7. Operation defaults (cath patients): urgency=elective, weight=isolated_cabg, thoracic_aorta=N
8. Critical preop: read AD+DC carefully, don't keyword-match. Y if IABP / ECMO / shock / acute resp failure / decomp HF / preop inotropes / VT-VF / preop ventilation / acute renal failure
9. ECA: strict definition — absent pulse or bruit alone does not qualify
10. Previous cardiac surgery: any pericardium-opening surgery counts (including aortic root / arch replacement)

============================================
  EMR session
============================================

- URL pattern: `http://hisweb.hosp.ncku/Emrquery/(S(SESSION_ID))/tree/frame.aspx`
- Session ID expires within hours — request a fresh one from user when needed
- Python `requests` works directly with the session URL (no cookies needed)
- Lab reports (Cr/echo) require opening EMROutcome.aspx tab; TreeView loads dynamically

============================================
  PHI policy reminder
============================================

This repo is PUBLIC. Never write to memory/, HANDOFF.md, or any tracked file:
  - Real chart numbers
  - Real patient names
  - Specific lab values tied to identifiers
  - Raw EMR text or screenshots

Patient-specific working data lives only in `_emr_raw/` (gitignored) and chat. Per-batch
result tables (chart / name / score) are reported in chat only — never committed.
