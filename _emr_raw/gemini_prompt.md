You are extracting EuroSCORE II form fields from EMR records (in Chinese + English).

Read the EMR text below and output a YAML file matching this exact schema:

```yaml
chart: "<8-digit chart number>"
name: "<Chinese name>"
admit: "YYYY-MM-DD"
dc: "YYYY-MM-DD"
sn: "<medical sn>"
age: <int>           # at admission date, computed from DOB
female: <bool>
weight_kg: <float>   # most recent weight before discharge
height_cm: <float>
cr_mg_dl: <float>    # most recent serum creatinine before discharge (CREA)
egfr: <float|null>   # eGFR if shown
nyha: I              # default I
ccs4: false          # default N. Only true if PI explicitly says "inability to perform any activity" or "angina at rest with no functional capacity". Chest pain at rest alone is NOT enough.
iddm: <bool>         # true ONLY if Order list mentions insulin/humulin/NPH/lantus/levemir/aspart/glargine/tresiba/toujeo/ryzodeg/novomix/actrapid/ryzodeg
extracardiac_arteriopathy: <bool>   # true if PL/Dx/PI mentions: claudication, PAOD, carotid stenosis >50%, carotid occlusion, amputation for arterial disease, prior or planned aortic/limb/carotid intervention
chronic_pulmonary_disease: <bool>   # true if Dx mentions COPD, asthma on chronic bronchodilator/steroid
poor_mobility: <bool>               # true ONLY if AD says "partially dependent", "dependent", "partially independent". "independent daily activity" → false
previous_cardiac_surgery: <bool>    # true if prior open-heart surgery (CABG, valve, congenital). PCI/cath/stent does NOT count.
active_endocarditis: <bool>         # true if currently on antibiotics for IE
critical_preop: <bool>              # true if Dx/PI/hospital course has ANY of: IABP, ECMO, shock, acute respiratory failure, decompensated heart failure, VT/VF/aborted SCD, preop cardiac massage, preop ventilation, preop inotropes, acute renal failure (anuria/oliguria <10ml/h)
lv_function: good                   # leave good if no echo. Or moderate (LVEF 31-50)/poor (21-30)/very_poor (≤20) if echo found.
recent_mi: <bool>                   # true if MI within 90 days of admission. Old MI (>90d) = false.
pa_systolic: none                   # leave none if no echo. Or 31_55 / ge_55 from PASP.
urgency: elective
weight_of_procedure: isolated_cabg
thoracic_aorta: false
manual_score: <unchanged from template>
```

In addition to the YAML above, output a `rationale:` dict at the END of the YAML, with one entry per non-default field. Format:

```yaml
rationale:
  field_key: "短句說明依據（例：AD: 'lives at home with independent daily activity' / DC hospital course / Order list / Echo 2026-02-11 LVEF 53%）"
```

Only include rationale for fields that are non-default (e.g. iddm: true, previous_cardiac_surgery: true, recent_mi: true, ECA: true, critical_preop: true, NYHA != I, ccs4: true, renal != normal, lv_function != good, pa_systolic != none). Skip default-value fields.

EMR text follows after this line:
---
