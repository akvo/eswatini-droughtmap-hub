# IKS Data — Information Needed to Properly Embed It

Mirror of the weather-station requirements list, for the IKS (Indigenous Knowledge Systems) feed.
Based on the actual instrument: KoboToolbox form `a3ytas3GLhSewNTZByCCsd` ("CDI-E - IKS by Akvo")
and the 2026-05-11 dummy export (107 submissions).

## 1. IKS submission & observer metadata

For each submission, one row:

```
submission_id | observer_id | observer_name | inkhundla | chiefdom | observed_at | submitted_at |
indicator_codes (multi) | indicator_details | soil_moisture | vegetation | photo_urls | validation_status
```

And a separate **observer registry** (the IKS equivalent of the station table):

```
observer_id | name | phone/contact | assigned_inkhundla | assigned_chiefdom(s) | trained_on | active (y/n)
```

Notes from the current form:
- The form captures observer **name as free text** (A1) — an observer ID/registry is needed for
  deduplication, completeness scoring ("how many of the expected observers reported this month?")
  and quality follow-up.
- `observed_at` vs `submitted_at` matters: Kobo gives `start`/`end`/`_submission_time`, but the
  *observation* date (when the indicator was seen) is not asked — worth adding to the form.

## 2. Data source and access method

- **Platform:** KoboToolbox (form asset UID `a3ytas3GLhSewNTZByCCsd`, "Clone of CDI-E - IKS by Akvo").
- **API:** KoboToolbox KPI REST API v2 is available:
  - Endpoint: `GET {kobo_server}/api/v2/assets/a3ytas3GLhSewNTZByCCsd/data.json` (also `.xlsx`, `.csv`)
  - Which server hosts the account? (kf.kobotoolbox.org / eu.kobotoolbox.org / self-hosted) — needed for the base URL
  - Auth: account API token (`Authorization: Token <key>`) — a service-account token is needed for the hub
  - Format: JSON (one record per submission; select_multiple as space-separated codes + one-hot columns in exports)
  - Update behaviour: near-real-time on submission; recommended hub sync: scheduled pull (e.g. hourly/daily Django-Q task) with `query={"_submission_time":{"$gt": ...}}` incremental filter; no meaningful rate limits at this volume
  - Media: photo attachments (D3) served via authenticated attachment URLs — decide whether the hub mirrors them
- **If API access is not granted:** scheduled XLSX/CSV export (like the file provided) delivered to
  cloud storage on an agreed cadence (weekly at minimum during the season).
- **Form versioning:** `__version__` is present per record — the hub importer must tolerate form
  revisions (new/renamed indicators) without dropping data.

## 3. Submission-to-Inkhundla mapping

This is the weakest point of the current form and the most important fix:

- A2 (constituency) and A3 (chiefdom) are **free-text** fields. In the dummy export, 0 of 106
  constituency values match a real Inkhundla. Real submissions will have spelling variants
  ("Pigg's Peak" / "Piggs Peak") that break joins.
- **Required:** convert A2/A3 to cascading `select_one` questions driven by the official list of
  59 Tinkhundla (+ chiefdoms per Inkhundla), using the same administration IDs as the hub's
  `Administration` table (`administration_id` from the CDI GeoJSON). The choice `name` should be
  the administration ID, not the label.
- Define the **aggregation rule** when one chiefdom-level report feeds an Inkhundla score, and the
  expected-reports baseline per Inkhundla (e.g. ≥ N observers × M chiefdoms) that underpins the
  completeness, confidence and agreement scoring in the DIH validation framework.

## 4. Indicator catalogue governance (IKS-specific extra)

The catalogue is the IKS equivalent of sensor calibration — it defines how raw observations become
a drought/rain signal:

- **Polarity sign-off:** each of the 29 indicators (21 rainfall B1 + 8 seasonal C1) needs an agreed
  meaning: predicts **rain** vs predicts **drought/dry season** (TWG/elders to confirm; the
  prototype's mapping covers 26 of 29 by code — T/P high temperatures, Sk clear sky, M/C tilted
  moon, B butterflies, FW white flowers lean drought).
- **Modifier questions:** B1.1/B1.6/B1.9/B1.12 capture *nature* of the observation (e.g. frogs
  croak louder = stronger rain signal) — define whether these weight the signal or are contextual.
- **Seasonal applicability windows:** several indicators are only meaningful in specific months
  (e.g. W wind East→West "September/October") — the scoring should ignore out-of-window reports.
- **D1/D2 ground-truth role:** soil-moisture (dry/moist/wet) and vegetation (green/some/brown)
  are direct observations, not predictions — agree whether they feed the *current* CDI agreement
  check (vs satellite soil moisture / NDVI) rather than the forecast signal.
