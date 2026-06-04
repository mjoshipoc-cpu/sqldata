# Gap Engine — Spec Authoring Guide

Everything a spec author needs to create a new measure JSON that runs against the
gap engine with **zero code changes**.

---

## 1. Evaluation Pipeline (Fixed Precedence)

The engine evaluates every member in this exact order and assigns **one** status:

| Order | Check | Status assigned |
|-------|-------|-----------------|
| 1 | `eligibility` fails | `NOT_IN_POPULATION` — member skipped entirely |
| 2 | Any `exclusions` branch passes | `EXCLUDED` — member not counted in rate |
| 3 | `numerator` passes | `COMPLIANT` — member met the measure |
| 4 | (none of the above) | `NON_COMPLIANT` — open care gap |

Only `COMPLIANT` + `NON_COMPLIANT` members form the denominator for the rate.

---

## 2. Top-Level Spec Structure

```json
{
  "measure_id":          "CBP",              // required — unique, used in API routes
  "measure_name":        "Controlling High Blood Pressure",  // required
  "version":             "MY2025",           // required
  "measure_type":        "proportion",       // optional, informational

  "measurement_period": {                    // required
    "start": "YYYY-MM-DD",
    "end":   "YYYY-MM-DD"
  },

  "eligibility":  { /* group */ },           // required
  "exclusions":   { /* group */ },           // required (can have empty criteria: [])
  "numerator":    { /* group */ }            // required
}
```

### Optional metadata fields (ignored by engine, useful for humans)

```json
"_spec_gaps":            ["..."],   // known limitations vs. the real spec
"_value_sets_required":  { ... },   // OID map for value set loader
"_note":                 "..."      // any comment on a block (engine ignores _-prefixed keys)
```

---

## 3. Groups — AND / OR / NOT

Any block with `"operator"` + `"criteria"` is a **group**. Groups can be nested arbitrarily.

```json
{
  "operator": "AND",          // "AND" | "OR" | "NOT"
  "criteria": [
    { /* criterion or nested group */ },
    { /* criterion or nested group */ }
  ]
}
```

| Operator | Passes when |
|----------|-------------|
| `AND` | **all** criteria pass |
| `OR` | **any** criterion passes |
| `NOT` | **none** of the criteria pass |

---

## 4. Leaf Operators (Criteria)

Every leaf criterion has an `"op"` key. Six operators are available.

---

### 4.1 `age_in_range`

Check member age as of a reference date.

```json
{
  "op":    "age_in_range",
  "min":   18,              // required — inclusive lower bound
  "max":   85,              // optional — inclusive upper bound; omit for "no upper limit"
  "as_of": "period_end"    // optional — "period_end" (default) | "period_start"
}
```

**Evidence returned:** `{ age, range: [min, max], passed }`

---

### 4.2 `gender`

Match member's administrative gender (case-insensitive).

```json
{
  "op":    "gender",
  "value": "F"          // "F" | "M" | any string stored in member demographics
}
```

**Note:** Engine uses the administrative gender field only. If your spec allows
"Sex Assigned at Birth" (LOINC 76689-9) or FHIR Sex Parameter extensions, note it
as a `_spec_gap` — the engine cannot evaluate those.

---

### 4.3 `continuous_enrollment`

Member must be enrolled for a lookback window ending at `period_end`, with a
maximum total gap.

```json
{
  "op":                    "continuous_enrollment",
  "lookback_months":       12,    // optional, default 12
  "allowable_gap_days":    45     // optional, default 45 — total gap allowed across the window
}
```

**How it works:** Clips each enrollment span to the window, sums all uncovered days,
and checks `total_gap <= allowable_gap_days`.

**Limitation:** Single combined gap allowance only. HEDIS multi-segment rules
(e.g., BCS-E: no gap in Oct–Dec, then ≤45 days/year for two years) cannot be
expressed exactly — approximate by combining the per-segment allowances.

---

### 4.4 `has_code`

Find events in a domain whose `(code_system, code)` tuple appears in a value set,
within a time window.

```json
{
  "op":         "has_code",
  "value_set":  "Mammography",           // string OR array of strings (union of sets)
  "domain":     "procedures",            // see Domain table below
  "window":     "period",                // see Window Tokens below
  "min_count":  1                        // optional, default 1
}
```

**`value_set` as array** — unions all named sets before matching:
```json
"value_set": ["FrailtyDevice", "FrailtyDiagnosis", "FrailtyEncounter", "FrailtySymptom"]
```

**Evidence returned:** `{ value_set, domain, window, found, min_count, matches[0..4], passed }`

---

### 4.5 `value_compare`

Compare a numeric field on events to a threshold.
Used for vitals (BP, BMI) and lab values.

```json
{
  "op":          "value_compare",
  "domain":      "vitals",          // typically "vitals" or "labs"
  "field":       "systolic",        // field name on the ClinicalEvent — see table below
  "comparator":  "<",               // "<" | "<=" | ">" | ">=" | "=="
  "threshold":   140,               // numeric value to compare against
  "window":      "period",          // see Window Tokens below
  "reading":     "most_recent",     // "most_recent" (default) | "any" | "all"
  "value_set":   "BPReadings"       // OPTIONAL — filter events to this value set first
}
```

**`reading` options:**
| Value | Passes when |
|-------|-------------|
| `most_recent` | the most recent reading in the window satisfies the comparison |
| `any` | at least one reading satisfies the comparison |
| `all` | every reading in the window satisfies the comparison |

**Numeric fields available on `ClinicalEvent`:**
| Field | Populated by | Typical use |
|-------|-------------|-------------|
| `systolic` | vitals loader | Systolic BP |
| `diastolic` | vitals loader | Diastolic BP |
| `value_numeric` | labs and vitals loader | Lab values, BMI, etc. |

---

### 4.6 `med_active`

Check for a dispensed medication (pharmacy claim) within a window.

```json
{
  "op":        "med_active",
  "value_set": "DementiaMedications",   // required — NDC codes
  "window":    "period_or_year_prior",  // see Window Tokens below
  "min_count": 1                        // optional, default 1
}
```

**Note:** Matches pharmacy claims only (the `pharmacy` domain). The value set must
contain NDC codes mapped in the value set store.

---

## 5. Window Tokens

Specify time windows for `has_code`, `value_compare`, and `med_active`.

| Token | Resolves to | Notes |
|-------|-------------|-------|
| `"period"` | `[period_start, period_end]` | The measurement year |
| `"anytime"` | `[1900-01-01, period_end]` | Full member history |
| `"prior_year"` | One year before the measurement period | Calendar year shift |
| `"period_or_year_prior"` | `[period_start − 1yr, period_end]` | Period + prior year combined |
| `"history_through_period_end"` | `[1900-01-01, period_end]` | Same as `anytime` |
| `"N_months_before_period_end"` | `[period_end − N months, period_end]` | Replace N with integer, e.g. `"24_months_before_period_end"` |
| `{"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}` | Explicit date range | Use when token precision is insufficient |

**When to use an explicit dict:** The `N_months_before_period_end` token uses
`relativedelta` which may land 1 day off from what a spec requires. Use an explicit
`{"from": ..., "to": ...}` when the window boundary is exact (e.g., BCS-E
mammography window starts Oct 1 exactly).

---

## 6. Domains

The `domain` field on `has_code` and `value_compare` refers to the type of clinical
event loaded for the member.

| Domain string | Event type | Loaded from | Key fields |
|---------------|-----------|-------------|------------|
| `"procedures"` | `PROCEDURE` | `03_claims_procedure.csv` | `code_system`, `code`, `event_date`, `modifier`, `place_of_service` |
| `"diagnoses"` | `DIAGNOSIS` | `04_claims_diagnoses.csv` | `code_system`, `code`, `event_date`, `place_of_service` |
| `"labs"` | `LAB` | `05_lab_results.csv` | `code_system`, `code`, `event_date`, `value_numeric`, `unit` |
| `"pharmacy"` | `PHARMACY` | `06_pharmacy_claims.csv` | `code_system`, `code` (NDC), `event_date`, `days_supply` |
| `"vitals"` | `VITAL` | `07_vitals.csv` | `code="VITAL"`, `event_date`, `systolic`, `diastolic`, `value_numeric` |

**Modifier and place-of-service:** Fields are loaded but no operator currently
filters by them. If a spec requires "CPT 19318 with modifier 50" or "exclude POS 81
claims", note it as a `_spec_gap`.

---

## 7. Value Set Store

Operators that use `value_set` look up `(code_system, code)` tuple sets from the
value set store, which is populated from `backend/real_data/08_hedis_value_sets.csv`.

### CSV schema

```
value_set_name, code_system, code, effective_year, is_active
Hypertension, ICD-10-CM, I10, 2025, TRUE
Mammography, CPT, 77067, 2024, TRUE
```

### Rules
- `code_system` and `code` are compared **case-insensitively** (stored as uppercase)
- `effective_year` must match the store's `effective_year` (default: 2025)
- `is_active` must be `TRUE` or `1`
- Missing value sets return an **empty set** (with a warning) — the operator
  silently fails to match. Check engine warnings when adding new measures.

### Adding value sets for a new measure
Add rows to `08_hedis_value_sets.csv` — no code changes required.
One row per code, with the correct `effective_year` for the measure.

---

## 8. Eligibility Skeleton

Minimal population entry pattern:

```json
"eligibility": {
  "operator": "AND",
  "criteria": [
    { "op": "age_in_range", "min": 18, "max": 75, "as_of": "period_end" },
    { "op": "gender", "value": "F" },
    { "op": "continuous_enrollment", "lookback_months": 12, "allowable_gap_days": 45 },
    {
      "op": "has_code",
      "value_set": "SomeCondition",
      "domain": "diagnoses",
      "window": "24_months_before_period_end",
      "min_count": 1
    }
  ]
}
```

Remove `gender` if the measure is gender-neutral.
Remove the `has_code` if there's no required condition for initial population.

---

## 9. Exclusions Skeleton

```json
"exclusions": {
  "operator": "OR",
  "criteria": [
    { "op": "has_code", "value_set": "Hospice", "domain": "diagnoses", "window": "period", "min_count": 1 },
    { "op": "has_code", "value_set": "Hospice", "domain": "procedures", "window": "period", "min_count": 1 },
    {
      "operator": "AND",
      "criteria": [
        { "op": "age_in_range", "min": 66, "as_of": "period_end" },
        { "op": "has_code", "value_set": "Frailty", "domain": "diagnoses", "window": "period", "min_count": 2 }
      ]
    }
  ]
}
```

If a measure has **no exclusions**, use:
```json
"exclusions": { "operator": "OR", "criteria": [] }
```

---

## 10. Numerator Skeleton

```json
"numerator": {
  "operator": "OR",
  "criteria": [
    {
      "op": "has_code",
      "value_set": "SomeServiceValueSet",
      "domain": "procedures",
      "window": "period",
      "min_count": 1
    }
  ]
}
```

For composite numerators (e.g., two separate screenings required), use `AND`:
```json
"numerator": {
  "operator": "AND",
  "criteria": [
    { "op": "has_code", "value_set": "ServiceA", "domain": "procedures", "window": "period", "min_count": 1 },
    { "op": "has_code", "value_set": "ServiceB", "domain": "procedures", "window": "period", "min_count": 1 }
  ]
}
```

For blood pressure control (value-based numerator):
```json
"numerator": {
  "operator": "AND",
  "criteria": [
    { "op": "value_compare", "domain": "vitals", "field": "systolic",  "comparator": "<", "threshold": 140, "window": "period", "reading": "most_recent" },
    { "op": "value_compare", "domain": "vitals", "field": "diastolic", "comparator": "<", "threshold": 90,  "window": "period", "reading": "most_recent" }
  ]
}
```

---

## 11. Known Engine Limitations (Spec Gaps to Document)

When a HEDIS or other payer spec requirement **cannot** be expressed with existing
operators, document it in `_spec_gaps` so the next engineer knows what's missing.

| Limitation | Example spec requirement | Workaround / note |
|------------|--------------------------|-------------------|
| **No modifier filtering** | CPT 19303 with modifier LT | Use left-specific value set if available |
| **No place-of-service filter** | Exclude POS 81 (lab) claims | Accept false positives; note in `_spec_gaps` |
| **No different-dates dedup** | ≥2 frailty events on different dates | `min_count: 2` may over-count same-day duplicates |
| **No multi-segment enrollment** | No gap Oct–Dec + ≤45/yr per year | Combine into single `allowable_gap_days` |
| **No death exclusion** | Exclude members deceased during period | No field on MemberProfile; always omitted |
| **No gender identity extensions** | LOINC 76689-9 sex assigned at birth | Admin gender only |
| **No same-line modifier detection** | Unilateral mastectomy + bilateral modifier on one claim | Cannot detect |

---

## 12. Full Minimal Example

```json
{
  "measure_id":   "COL-E",
  "measure_name": "Colorectal Cancer Screening (Exchange)",
  "version":      "MY2024",
  "measure_type": "proportion",
  "measurement_period": { "start": "2024-01-01", "end": "2024-12-31" },

  "eligibility": {
    "operator": "AND",
    "criteria": [
      { "op": "age_in_range", "min": 45, "max": 75, "as_of": "period_end" },
      { "op": "continuous_enrollment", "lookback_months": 12, "allowable_gap_days": 45 }
    ]
  },

  "exclusions": {
    "operator": "OR",
    "criteria": [
      { "op": "has_code", "value_set": "Hospice",                     "domain": "diagnoses",  "window": "period",  "min_count": 1 },
      { "op": "has_code", "value_set": "ColorectalCancerDiagnosis",   "domain": "diagnoses",  "window": "anytime", "min_count": 1 },
      { "op": "has_code", "value_set": "TotalColectomy",              "domain": "procedures", "window": "anytime", "min_count": 1 }
    ]
  },

  "numerator": {
    "_note": "Any colorectal screening in the last 10 years or colonoscopy in past 10 years.",
    "operator": "OR",
    "criteria": [
      { "op": "has_code", "value_set": "FIT_DNA",          "domain": "procedures", "window": "period",                         "min_count": 1 },
      { "op": "has_code", "value_set": "FOBT",             "domain": "procedures", "window": "period",                         "min_count": 1 },
      { "op": "has_code", "value_set": "FlexibleSigmoid",  "domain": "procedures", "window": "60_months_before_period_end",    "min_count": 1 },
      { "op": "has_code", "value_set": "Colonoscopy",      "domain": "procedures", "window": "120_months_before_period_end",   "min_count": 1 },
      { "op": "has_code", "value_set": "CTColonography",   "domain": "procedures", "window": "60_months_before_period_end",    "min_count": 1 }
    ]
  },

  "_value_sets_required": {
    "FIT_DNA":                   "2.16.840.1.113883.3.464.1004.1420",
    "FOBT":                      "2.16.840.1.113883.3.464.1004.1093",
    "FlexibleSigmoid":           "2.16.840.1.113883.3.464.1004.1102",
    "Colonoscopy":               "2.16.840.1.113883.3.464.1004.1063",
    "CTColonography":            "2.16.840.1.113883.3.464.1004.1421",
    "ColorectalCancerDiagnosis": "2.16.840.1.113883.3.464.1004.1065",
    "TotalColectomy":            "2.16.840.1.113883.3.464.1004.1250",
    "Hospice":                   "2.16.840.1.113883.3.464.1004.1761"
  }
}
```

---

## 13. Checklist Before Handing Off a Spec

- [ ] `measure_id` is unique — check `backend/specs/` for conflicts
- [ ] All `value_set` names exist as rows in `08_hedis_value_sets.csv` (or add them)
- [ ] `effective_year` in value set CSV matches the store's year (default 2025)
- [ ] All `window` tokens are valid — no typos (engine throws `ValueError` on unknown tokens)
- [ ] All `domain` strings are lowercase and plural (`"procedures"`, `"diagnoses"`, `"vitals"`, `"labs"`, `"pharmacy"`)
- [ ] `op` strings match exactly: `age_in_range`, `gender`, `continuous_enrollment`, `has_code`, `value_compare`, `med_active`
- [ ] Any spec requirements that couldn't be modelled are listed in `_spec_gaps`
- [ ] `_value_sets_required` block lists every value set name referenced in the spec with its OID
- [ ] Place spec file in `backend/specs/<MEASURE_ID>.json` — backend auto-loads on startup
