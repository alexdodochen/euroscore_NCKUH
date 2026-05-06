============================================
  HANDOFF — Last Updated: 2026-05-06
============================================

[What this session did]
  1. Computed EuroSCORE II for 6 cardiac admission patients (1 elective post-cath, 5 acute ICU presentations including ESRD/IABP/intubated cases).
  2. Reorganized the per-attending evaluation sheet block into 4 visually grouped sections with green-band dividers (demographic+renal / comorbidity Y/N / cardiac / operation).
  3. Distilled 3 generalizable scoring rules from this batch into PHI-safe `memory/rule_*.md` files.

[Current state]
  - Branch: main, has staged + committed changes from this session
  - Latest commit will include: per-attending sheet ITEMS reorder + 3 memory rule files + HANDOFF refresh
  - Deploy state: N/A (local computation tool, no deployment)

[Next steps]
  - On the next batch, drive `discover_sns_pw.py` -> `fetch_via_pw.py` -> per-patient YAML -> `cheatsheet.py` -> `bootstrap_workbook.py` -> `generate_euroscore_sheet.py` -> `write_to_excel.py` -> `mdcalc_sheet.py`
  - Apply the three new rules from the start: order-based IDDM, calendar-year age, NYHA evaluated from EMR (never default I)
  - For active inpatient admissions, `fetch_via_pw.py` auto-detects iviewer.aspx vs viewer/viewer_v2.aspx; raw `requests` against viewer.aspx for active admissions returns IndexOutOfRangeException

[Known issues / blockers]
  - None

[Don't repeat these mistakes]
  - Do NOT default NYHA to I — read AD Present Illness / ROS and assign clinically (rule_nyha_from_emr.md)
  - Do NOT use the EMR AD-displayed age — use calendar-year subtraction (rule_age_calendar_year.md)
  - Do NOT apply the strict "preop chronic insulin" interpretation for IDDM — any in-hospital insulin order is Y (rule_iddm_in_hospital_insulin.md)
  - Do NOT delegate EMR raw text to gemini — main agent must read it directly (CLAUDE.md global PHI policy)
  - Excel master col J should hold the percentage string ("X.XX%"), not decimal 0.0X
  - Output blocks (per-attending sheet AND chat tables) follow the user's section grouping, separated by colored divider rows

[Relevant files]
  - euroscore_ii.py — Nashef 2012 Table 6 coefficients + Cockcroft-Gault + renal_category
  - cheatsheet.py — YAML -> MDCalc-style stratified cheatsheet + diff vs manual
  - fetch_patient.py — direct EMR doc fetch via Python requests (discharged admissions, viewer/viewer_v2)
  - fetch_via_pw.py — Playwright fetcher with active-vs-discharged detection (active admissions need iviewer.aspx)
  - discover_sns_pw.py — Playwright chart-switch + leftFrame medicalsn enumeration
  - bootstrap_workbook.py — build EURO-CR.xlsx master sheet from existing per-patient YAMLs (fresh-clone setup)
  - generate_euroscore_sheet.py — builds the per-attending evaluation sheet, ITEMS now grouped into 4 sections with green divider bands
  - write_to_excel.py — writes score back to master col J as "X.XX%" string + per-block detailed cells
  - mdcalc_sheet.py — adds a sheet whose row order matches the hospital MDCalc form UI
  - keyin_sheet.py — console output of the same MDCalc-order layout for copy-paste verification
  - _emr_raw/<chart>.yaml — per-patient input (gitignored, contains PHI)
  - _emr_raw/gemini_prompt.md — schema for the YAML extraction (used as reference; main agent does the extraction itself, not gemini)

[Important memory files]
  - MEMORY.md (index)
  - rule_iddm_in_hospital_insulin.md
  - rule_age_calendar_year.md
  - rule_nyha_from_emr.md

============================================
  Workflow (per patient, fresh-clone path)
============================================

1. Discover medicalsns: `python discover_sns_pw.py <SESSION_ID> <chart1> [<chart2> ...] --start 2026-01-01 --stop 2026-08-01`
2. Identify the correct admission I-sn by matching admission date in `_emr_raw/<chart>_left.html`
3. Fetch EMR docs: `python fetch_via_pw.py <SESSION_ID> <chart>:<I_SN>,<O_SN_1>,<O_SN_2> ...` — auto-detects active (iviewer) vs discharged (viewer/viewer_v2)
4. Split sections: `python _emr_raw/split_sections.py` to inspect AD/DC/PL/diagnosis/order independently
5. Read AD/DC for clinical comorbidity judgment (do NOT delegate to gemini):
   - critical_preop: IABP / ECMO / shock / decomp HF / acute resp failure / inotropes / VT-VF / preop ventilation / acute renal failure
   - ECA: claudication / carotid >50% / amputation / prior or planned aortic-limb-carotid intervention (absent pulse alone does NOT count)
   - previous_cardiac_surgery: any pericardium-opening procedure (PCI / cath / PTA do NOT count; ORIF does NOT count)
   - recent_mi: acute MI within 90 days (unstable angina != MI; chronic CKD-related stable troponin elevation != acute MI)
   - poor_mobility: AD describes daily activity; "independent" -> N, "partially dependent / nearly bedridden" -> Y
   - NYHA: read PI/ROS for effort tolerance, never default to I (see rule_nyha_from_emr.md)
6. Grep order list for insulin keywords (any hit -> iddm Y; see rule_iddm_in_hospital_insulin.md)
7. Write `_emr_raw/<chart>.yaml` with all 21 fields + rationale dict for the 13 clinical fields. Use calendar-year age (see rule_age_calendar_year.md).
8. Score it: `python cheatsheet.py _emr_raw/<chart>.yaml`
9. Bootstrap workbook (if EURO-CR.xlsx doesn't exist yet): `python bootstrap_workbook.py`
10. Generate per-attending sheet: `python generate_euroscore_sheet.py <attending-name>`
11. Write back: `python write_to_excel.py`
12. Add MDCalc-order sheet: `python mdcalc_sheet.py`
13. Report results in chat using the standard summary table format. Report stays in chat only — never commit patient identifiers to this public repo.

============================================
  Per-attending sheet block layout (after 2026-05-06 redesign)
============================================

Each patient block in `<attending> Euroscore評估表` is grouped into 4 sections with green divider bands:

  Section 1 (demographic + renal): age / gender / weight / Cr / CC / renal grade
  ── divider ──
  Section 2 (comorbidity Y/N): ECA / poor mobility / previous cardiac surgery (Redo) / chronic lung disease / active endocarditis / critical preop / IDDM
  ── divider ──
  Section 3 (cardiac): NYHA / CCS class 4 / LV function / recent MI (90d) / PA systolic
  ── divider ──
  Section 4 (operation): urgency / weight of procedure / thoracic aorta surgery
  ── final ──
  EuroSCORE II predicted mortality (highlighted yellow)

============================================
  EMR session
============================================

- URL pattern: `http://hisweb.hosp.ncku/Emrquery/(S(SESSION_ID))/tree/frame.aspx`
- Session ID expires within hours — request a fresh one from user when needed
- Cookieless ASP.NET session bound to URL; any process using the same URL shares state
- `list.aspx` (the leftFrame tree) is JS-driven; raw `requests` cannot enumerate medicalsns. Use Playwright (`discover_sns_pw.py`).
- Active inpatient admissions use `iviewer.aspx` for AD/PL/diagnosis/order/consult; raw `viewer.aspx` returns `IndexOutOfRangeException` for these. Discharged admissions use `viewer.aspx` and `viewer_v2.aspx`. `fetch_via_pw.py` auto-detects which.

============================================
  PHI policy reminder
============================================

This repo is PUBLIC. Never write to memory/, HANDOFF.md, or any tracked file:
  - Real chart numbers
  - Real patient names
  - Specific lab values tied to identifiers
  - Raw EMR text or screenshots

Patient-specific working data lives only in `_emr_raw/` (gitignored) and chat. Per-batch result tables (chart / name / score) are reported in chat only — never committed.
