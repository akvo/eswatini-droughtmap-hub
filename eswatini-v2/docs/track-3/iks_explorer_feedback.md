# Feature Design: Track 3 Operational Response - IKS Explorer Refinement

**Task ID**: IKS-Feedback
**Issue**: #109
**Author**: Galih Pratama
**Date**: 2026-07-17
**Status**: [STATUS: IMPLEMENTED]

---

## 1. Context & Problem Statement

Following the initial implementation of the live backend integration and redesign of the Indigenous Knowledge System (IKS) Explorer, we received feedback to adjust visual elements, labels, and color profiles to align with the platform's standard design language:

```text
Currently:
- The line chart visibility toggle and legends display "Drought-leaning", which should be "Extreme weather-leaning".
- The monthly status grids (soil moisture & vegetation greenness) display day numbers behind the month labels (e.g. "May 01", "May 08") instead of the year (e.g. "May 2026").
- The vegetation greenness card title includes "D2", which needs to be removed.
- The page color profile is too white/bright and lacks the neutral, grey-ish background used by other Track 3 components (e.g., the Activity Library).
- Tooltips and observation monthly charts are too small to read comfortably.

Goal:
- Update labels, card titles, backgrounds, date formatting, and tooltip sizes to deliver a premium, neutral, and readable experience.
```

---

## 2. Requirements

### User Acceptance Criteria

- [x] **Labels**: Line chart checkbox filters, labels, and bottom legends display **"Extreme weather-leaning"** instead of "Drought-leaning".
- [x] **Grid Dates**: Soil Moisture and Vegetation Greenness status grids display months and years (e.g., `"May 2026"`, `"Jun 2026"`) instead of days (`"May 01"`, `"May 08"`).
- [x] **Card Titles**: Vegetation greenness grid title is updated to **"Vegetation greenness (Tiluhlata / Timbalwa letiluhlata / Bushile)"** (without "D2").
- [x] **Background Contrast**: The page layout incorporates a soft, neutral grey-ish background (`bg-neutral-50` / `bg-[#f8f9fa]`) to increase visual contrast and prevent an excessively white UI, matching the Activity Library look.
- [x] **Chart Tooltips**: ECharts tooltips and fonts in the monthly observations graph are larger and more readable.

### Technical Acceptance Criteria

- [x] Modify `backend/api/v1/v1_iks/views.py` and mock file `iks_data.json` to replace date numbers in the `weeks` array with year numbers (e.g. `"May 2026"` / `"Jun 2026"`).
- [x] Update frontend React components `MonthlyStatusGrid` and `IksTab` to process the updated `weeks` array.
- [x] Update mock interceptor logic in `frontend/src/lib/api.js` to match the updated response payloads.
- [x] Adjust wrapper styling classes in the parent insights tab container to apply the neutral grey background.
- [x] Update frontend Jest unit tests and backend unit tests to verify the corrected labels and payload shapes.

---

## 3. Proposed Changes

### Backend

#### [MODIFY] [views.py](backend/api/v1/v1_iks/views.py)

Update `IKSSoilTrendAggregationView` to dynamically compute and return the last 12 calendar months as unique `"Month Year"` keys (e.g. `["Aug 2025", "Sep 2025", ..., "Jul 2026"]`) and group count aggregations under these 12 months:

```python
from dateutil.relativedelta import relativedelta

now = timezone.now()
months_list = [now - relativedelta(months=i) for i in range(11, -1, -1)]
weeks = [m.strftime("%b %Y") for m in months_list]
month_to_idx = {(m.year, m.month): idx for idx, m in enumerate(months_list)}
```

---

### Frontend

#### [MODIFY] [iks_data.json](frontend/src/static/iks_data.json)

Update the mock `weeks` list to contain 12 distinct calendar months matching the last 12 months (e.g., matching the indicator activity/series monthly format):

```json
{
  "weeks": [
    "Aug 2025",
    "Sep 2025",
    "Oct 2025",
    "Nov 2025",
    "Dec 2025",
    "Jan 2026",
    "Feb 2026",
    "Mar 2026",
    "Apr 2026",
    "May 2026",
    "Jun 2026",
    "Jul 2026"
  ]
}
```

#### [MODIFY] [api.js](frontend/src/lib/api.js)

Ensure the local mock fallback interceptors match the updated `iks_data.json` structure for the `/iks/aggregations/soil-trend` endpoint.

#### [MODIFY] [IksTab.js](frontend/src/components/Insights/IksTab/IksTab.js)

- Update checkbox label, bottom legends, and descriptions from `"Drought-leaning"` to `"Extreme weather-leaning"`.
- Remove `"D2 "` prefix from `MonthlyStatusGrid` vegetation greenness title.
- Adjust chart config `tooltip` font size and dimensions to make it larger.
- Add wrapping outer div styles to inject the grey background color (`bg-neutral-50`) around elements.

---

## 4. Verification Plan

### Automated Tests

- Run backend tests:

  ```bash
  docker compose exec backend ./test.sh
  ```

- Run frontend Jest tests:

  ```bash
  docker compose exec frontend ./test.sh
  ```

### Manual Verification

- View `/detailed-insights?tab=iks` anonymously.
- Check that the soil moisture and vegetation greenness months show years (e.g., `"May 2026"`) instead of dates (e.g. `"May 01"`).
- Verify the background is a soft grey color and the charts show `"Extreme weather-leaning"` labels.

---

## 5. Estimation

| Task | Min Hours | Max Hours | Confidence |
| :--- | :--- | :--- | :--- |
| T1: Update backend views weeks arrays | 0.5 | 1.0 | High |
| T2: Update frontend labels, legends, and grey background | 1.0 | 2.0 | High |
| T3: Update mock files and api.js mappings | 0.5 | 1.0 | High |
| T4: Run verification test suites | 0.5 | 1.0 | High |
| **Total** | **2.5** | **5.0** | **High** |
