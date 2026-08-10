// key/field mirror backend CS_SENSORS; wind_speed has no reading field.
export const SENSOR_OPTIONS = [
  { key: "min_temp", label: "Min temperature", field: "min_temperature" },
  { key: "max_temp", label: "Max temperature", field: "max_temperature" },
  { key: "rain_gauge", label: "Rain gauge", field: "precipitation" },
  { key: "soil_moisture", label: "Soil moisture", field: "soil_moisture" },
  // keys must match backend CS_SENSORS — this one is not abbreviated
  {
    key: "soil_temperature",
    label: "Soil temperature",
    field: "soil_temperature",
  },
  { key: "wind_speed", label: "Wind speed", field: null },
];

export const STATION_TYPES = [
  "Not specified",
  "Davis Vantage Pro2",
  "Manual gauge + digital thermometer",
  "Automatic weather station (other)",
  "School-built station",
];

export const NUDGE_TONES = {
  friendly: {
    label: "Friendly nudge",
    message:
      "Sanibonani {name}, hope you're well. Just a gentle reminder that we haven't received your {month} reading yet — no pressure, just checking that everything is OK at the station. Click the link below to submit whenever it suits you. Siyabonga.",
    subject: "Just checking in — your {station} {month} reading",
  },
  formal: {
    label: "Formal follow-up",
    message:
      "Dear {name}, this is a follow-up regarding the outstanding {month} weather reading for {station}. We would appreciate your submission at your earliest convenience. Please use the link below to access the form.",
    subject: "Follow-up: {station} {month} reading outstanding",
  },
  concerned: {
    label: "Concerned check-in",
    message:
      "Sanibonani {name}, we noticed we haven't heard from you in a while and wanted to make sure everything is alright — both with you and the station. If anything has changed or you need help, please let us know. We value your contribution to the network. Siyabonga.",
    subject: "Checking in — is everything OK at {station}?",
  },
};
