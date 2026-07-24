# Citizen Science Weather · design brief

*Companion brief to `citizen-science-weather-mockup.html`. Written to be handed to a designer to formalize in Figma.*

---

## 1 · What this is

A sister platform to the Drought Intelligence Hub (DIH) where community volunteers submit **monthly weather readings** from their assigned UNESWA weather station. It is **not embedded** in the DIH — it has its own URL, its own sign-in, its own database — but it is **visually part of the same family** (same fonts, palette, tone) so observers understand they are contributing to the same national effort.

The core loop is simple: on the 1st of every month, every observer receives an email with a one-click link to a form. They fill in what their station recorded. That's it.

---

## 2 · Users and roles

**Observer** · One person per weather station. Enters their own station's readings, sees their own history, cannot see other stations. Auth is passwordless — magic link sent to their email each month.

**Admin** · UNESWA + NDRMA staff. Sees all stations, all observers, all data. Can add/remove stations and observers, trigger reminder emails, export the dataset, and nudge specific observers who are falling behind.

There are **no other roles** in the v1 platform. TWG members and the general public do not access this tool — the data is pushed to the DIH after admin review.

---

## 3 · Auth model — magic link via email

There is no username + password.

- Each observer is registered by the admin with their name, email, and assigned weather station.
- On the 1st of every month, an automated email goes out (see §5 for content). It contains a one-click **"Submit reading"** button that carries a signed token in the URL.
- Clicking the button logs the observer in for a 7-day session and takes them straight to the form for the current month.
- If they lose the email or the token expires, they can request a fresh link from the fallback sign-in page (§6.1) by entering their email address.

**Why this shape:** observers may not be technical users, may not have password managers, and may only touch this tool once a month. Passwordless removes the friction that would otherwise silently reduce reporting rates.

---

## 4 · Fields observers submit

All fields are **optional**. The tool never blocks submission for a missing field.

| Field | Unit | Notes |
|---|---|---|
| Monthly minimum temperature | °C | Lowest reading recorded across the month |
| Monthly maximum temperature | °C | Highest reading recorded across the month |
| Monthly aggregated precipitation | mm | Total rainfall across the month |
| Average soil moisture | % or m³/m³ | Skip if station has no soil probe |
| Average soil temperature | °C | Skip if station has no soil probe |
| Notes | free text | Broken sensor? Unusual event? Story from the Inkhundla? |

The form makes it very visible that skipping is fine. The design uses a **progress bar showing how many fields are filled** (e.g. "2 of 5") rather than any red required-field indicators, and there is a copy block that explicitly reads *"You don't have to fill every field."*

---

## 5 · Reminder email

The reminder email is the primary entry point to the tool — most observers will only ever open the form via this email.

Design elements (see mockup):

- **From:** *Citizen Science Weather · DIH Eswatini*
- **Subject:** Personalized — e.g. *"Your Big Bend weather reading for May is due"*
- **Greeting:** In siSwati where appropriate (*"Sanibonani [Name]"*)
- **Station card:** A visually distinct block showing the observer's station name and location — signals *"this email is for you, not a mass send"*
- **Big CTA button:** "Submit May 2026 reading →" · magic-link URL
- **What-to-fill-in list:** The five fields as a short bulleted list, each with a small colored icon
- **"Not mandatory" callout:** Warm amber block reminding the observer that partial submissions are fine
- **Footer:** "Not the right person? Forward this email and let us know." + a support phone number

The email is sent automatically on the 1st of every month at 07:00 local time. Admins can also trigger it ad-hoc from the admin dashboard.

---

## 6 · Screens

### 6.1 Sign-in fallback

A simple centered card. Weather icon, headline, one email input, one button ("Send me a sign-in link"). Below the input: a short explanation of the passwordless model. This screen is only reached when someone loses their reminder email or navigates directly to the URL.

### 6.2 Observer form (post-login)

The main working screen. Structure:

- **App header** with logo, station name, observer name + sign-out.
- **Hero card** (navy background) with the month name in a green pill, a personalized headline (*"Sanibonani Sipho — let's log May's weather"*), and a **progress bar** showing filled-in fields (`2 of 5`).
- **Five field cards** in a 2-column grid. Each card has a colored icon (blue for T min, red for T max, blue-drop for rainfall, purple for soil moisture, amber for soil temperature), the field label, unit pill, input box, and one line of helper text.
- **Sixth "reassurance" card** in the grid making it very clear all fields are optional.
- **Notes card** with a large textarea for free-form observations.
- **Actions bar**: "Save draft" and "Submit" buttons.
- **History section** below: a running 12-month table of past submissions with a big **"You've reported 10 of 12 months (83%)"** completeness indicator at the top.

The completeness indicator matches the [data completeness metric](#) already defined for stations elsewhere in the DIH — one point per month reported, out of the trailing 12. This is a **motivational element**, not just a stat.

### 6.3 Admin dashboard

- **App header** with an admin-style "⚙" logo (charcoal, not green) so it's clear this is a different mode.
- **Network overview headline** + summary stats in four cards: Total stations · Reporting well (≥ 10/12) · At risk (missed 3+) · Reminders sent this month.
- **Toolbar** with filter chips (status + region) and three action buttons: Export CSV · Trigger reminders · Add station/observer.
- **Stations table** with columns: Station (name + location) · Observer (name + email) · Last submission · 12-month completeness (bar + %) · Actions (View · Nudge).
- Row-level "Nudge now" button lights up (green) for stations currently at risk — admin can send an ad-hoc reminder to that observer directly.

### 6.4 Add station + observer

Reached from the "+ Add station / observer" button in the admin toolbar. **One unified form registers both the station and its observer in one go**, because they always come as a pair — a new station has no operational meaning until it has someone submitting for it.

Two side-by-side sections:

**Section 1 · Weather station details**
- Station name (free text)
- Inkhundla (searchable dropdown grouped by region — 59 Tinkhundla total across Hhohho, Manzini, Lubombo, Shiselweni)
- Region (auto-filled from the Inkhundla choice — non-editable)
- Agro-ecological zone (auto-filled from the Inkhundla choice — one of Highveld, Middleveld, Lowveld or Lubombo Plateau — non-editable). This links each new station to the AEZ layer already used elsewhere in the DIH for climate-zone reporting.
- Latitude + longitude (decimal degrees, WGS84) with a **mini-map preview** showing an outline of Eswatini and a pin at the entered coordinates. A "✓ inside Eswatini" badge validates the coordinates fall inside the country boundary; entries outside the country show a warning.
- Sensors present (multi-select chips: min temp, max temp, rain gauge, soil moisture, soil temperature, wind speed) — **this determines which fields the observer sees on their monthly form.** A station without a soil-moisture probe never asks its observer for that value.
- Station type / model (dropdown — Davis Vantage Pro2, manual gauge + thermometer, other, school-built, etc.) — optional

**Section 2 · Observer details**
- Full name
- Email (primary — also the login handle)
- Phone (fallback — optional)
- Preferred language (English / siSwati toggle)
- Admin notes (visible only to other admins — e.g. "chairs the local DRMC, best reached after 15:00")
- Assigned admin (dropdown of UNESWA + NDRMA staff — who is responsible for following up if this observer stops reporting)

Below the two sections, a **welcome email preview card** shows exactly what the observer will receive on save — with their name, station and Inkhundla already inserted. This preview updates live as the form is filled in.

Bottom action bar:
- "Send welcome email now" toggle (on by default) — allows saving a station without inviting the observer yet, useful when the observer is not yet identified
- Cancel · Save + send welcome email buttons

**Design intent:** the form is deliberately two-column (station left, observer right) rather than a wizard, because both are needed and swapping between steps mid-fill is common — the admin might realise mid-way through the observer details that the Inkhundla is wrong. The live preview and mini-map reduce the need to save-and-check.

---

## 7 · Visual language

The tool sits in the DIH visual family but shifts the accent to signal *"citizen-facing tool, not the operational dashboard"*:

- **Primary dark:** DIH navy `#1C2B3A` (same as main platform, provides visual continuity)
- **Brand accent:** Akvo green `#00B98E` — the CTA color and the "positive" signal throughout
- **Attention accent:** warm gold `#F5B840` — used for reminders, in-progress badges, the "not mandatory" callout
- **Alert:** terracotta `#B85042` for the at-risk stations
- **Background:** warm off-white `#F5F5F0` on the app screens, `#FBF8F1` cream on prompt boxes
- **Typography:** Cambria (or an accessible serif) for headings; system sans (Segoe UI / SF Pro) for body. Same combo as the DIH.

**Iconography:** Small friendly emoji-style icons (weather-themed) instead of technical UI icons. This platform is used by non-technical observers — the tool should feel welcoming, not clinical.

**Voice:** Warm, second-person, personalised. Uses observer name and station name wherever it can. Says "Sanibonani" not "Login". Says "Let's log May's weather" not "Data entry form".

---

## 8 · Language

**Primary:** English. **Secondary:** siSwati where it matters — the greeting (*"Sanibonani"*), the polite closer (*"Siyabonga"*). Full multi-language toggle is not required for v1 but should be **easy to add later** — treat every string in the UI as translatable.

---

## 9 · Mobile

Observers will predominantly submit from **mobile phones**, often on the same phone that took the field reading. All screens must be responsive:

- The observer form's 2-column grid collapses to 1 column on narrow screens.
- The admin table becomes a card list on narrow screens.
- Buttons stay finger-friendly (min 44 px tap targets).
- No hover-dependent affordances anywhere — everything works with tap.

---

## 10 · Out of scope for v1

Explicitly not building for the first version:

- Real-time station telemetry (this is monthly, human-entered)
- Multi-observer per station
- Photo attachments (nice-to-have for v2)
- In-app messaging between admins and observers (they use email + phone)
- Public read access
- SMS-based reminders (email only in v1 — SMS is v2 if data shows email misses)

---

## 11 · Integration with the DIH

Data flows *out* of Citizen Science Weather *into* the DIH after admin review — the DIH does not read directly from this tool's live database. This preserves separation of concerns and gives UNESWA/NDRMA a chance to review anomalous readings before they hit the operational risk model.

A monthly export job runs on the 6th of every month (a day after the observer submission deadline) and feeds cleaned, admin-approved records into the DIH's weather-station data table.

---

## 12 · Success signals

The tool is working if:

- ≥ 80 % of registered observers submit a reading within the first 5 days of each month
- ≥ 3 of the 5 quantitative fields filled in on average per submission
- Notes field used in ≥ 20 % of submissions (indicates observers feel free to add context)
- Admin dashboard is opened at least weekly by an UNESWA or NDRMA admin
- < 5 % of observers "churn" (stop submitting) in a 6-month window after onboarding

---

## 13 · Handover to designer

The accompanying HTML file (`citizen-science-weather-mockup.html`) is a **clickable prototype** — not a final visual design. It shows layout, information hierarchy, copy tone, and interaction flow. Designers are expected to:

- Rebuild in Figma using the DIH design system
- Polish the iconography (currently emoji placeholders — replace with a proper icon set)
- Formalize the type scale (currently rough)
- Add hover, focus, active and disabled states for every interactive element
- Consider accessibility (contrast, keyboard navigation, screen reader labels) — the mockup does not fully address this
- Consider empty states (no history yet, no observers yet, station without soil probe)

Copy text in the mockup is intentional and **should be preserved** unless there's a compelling reason to change it — it was written for citizen scientists, not for internal Akvo review.
