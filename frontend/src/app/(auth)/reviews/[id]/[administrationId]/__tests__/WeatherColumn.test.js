import { render, screen } from "@testing-library/react";
import { WeatherColumn } from "../IndividualReview";

const metWeather = {
  data: [
    {
      key: "min_temperature",
      label: "Min temperature",
      value: 12,
      units: "°C",
    },
    {
      key: "soil_temperature",
      label: "Soil temperature",
      value: null,
      units: "°C",
      meta: { reason: "pending_sensor" },
    },
  ],
  meta: { resolution: "region_station", station: "Mbabane" },
};

const csReading = {
  data: [
    {
      key: "precipitation",
      label: "Precipitation (monthly)",
      value: 55,
      units: "mm",
    },
    { key: "soil_moisture", label: "Soil moisture", value: null, units: "%" },
  ],
  meta: {
    network: "citizen_science",
    station: "Big Bend Community",
    period: "2026-05",
    notes: "gauge overflowed on the 14th",
  },
};

describe("WeatherColumn (MET + citizen-science blocks)", () => {
  it("renders both blocks when both sources have data", () => {
    render(<WeatherColumn weather={metWeather} citizenScience={csReading} />);
    expect(screen.getByText("MET weather information")).toBeInTheDocument();
    expect(screen.getByText("Mbabane")).toBeInTheDocument();
    expect(
      screen.getByText("Citizen science weather station"),
    ).toBeInTheDocument();
    expect(screen.getByText("Big Bend Community")).toBeInTheDocument();
    expect(screen.getByText("55")).toBeInTheDocument();
    // null readings (soil temperature, soil moisture) render as "—", plus the
    // rainfall headline: this fixture carries no precipitation row.
    expect(screen.getAllByText("—")).toHaveLength(3);
    expect(
      screen.getByText("Observer notes: gauge overflowed on the 14th"),
    ).toBeInTheDocument();
  });

  it("renders the CS empty state when there is no submission", () => {
    const noData = {
      data: null,
      meta: { reason: "no_citizen_science_for_period" },
    };
    render(<WeatherColumn weather={metWeather} citizenScience={noData} />);
    expect(
      screen.getByText(
        "No citizen science weather observation submission for this Inkhundla this month.",
      ),
    ).toBeInTheDocument();
  });

  it("keeps MET strict per-region while CS renders independently", () => {
    const fallback = {
      ...metWeather,
      meta: { ...metWeather.meta, resolution: "nearest_station_fallback" },
    };
    render(<WeatherColumn weather={fallback} citizenScience={csReading} />);
    expect(
      screen.getByText(/No data available — no weather station/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Citizen science weather station"),
    ).toBeInTheDocument();
    expect(screen.getByText("Big Bend Community")).toBeInTheDocument();
  });

  it("names the month and the days reported so a thin month reads as thin", () => {
    const june = {
      ...metWeather,
      meta: { ...metWeather.meta, period: "2026-06", days_reported: 6 },
    };
    render(<WeatherColumn weather={june} citizenScience={null} />);
    expect(screen.getAllByText(/Jun 2026 · 6 days reported/)).toHaveLength(2);
  });

  it("says which month is empty when the region's station has no readings", () => {
    const empty = {
      data: null,
      meta: { reason: "no_station_data_for_period", period: "2026-06" },
    };
    render(<WeatherColumn weather={empty} citizenScience={null} />);
    // resolution is absent, so the strict per-region gate still applies
    expect(
      screen.getByText(/No data available — no weather station/),
    ).toBeInTheDocument();
  });

  it("headlines the monthly rainfall total in mm, never an SPI value", () => {
    const withRain = {
      ...metWeather,
      data: [
        ...metWeather.data,
        {
          key: "precipitation",
          label: "Precipitation (monthly)",
          value: 52.3,
          units: "mm",
        },
      ],
    };
    render(<WeatherColumn weather={withRain} citizenScience={null} />);
    // Once in the headline, once in the MET station card below it.
    expect(screen.getAllByText("52.3")).toHaveLength(2);
    expect(screen.getByText(/Monthly rainfall total/)).toBeInTheDocument();
    expect(screen.queryByText(/SPI/)).not.toBeInTheDocument();
  });

  it("does not leak a fallback station's rainfall into the headline", () => {
    const fallback = {
      ...metWeather,
      data: [
        {
          key: "precipitation",
          label: "Precipitation (monthly)",
          value: 52.3,
          units: "mm",
        },
      ],
      meta: { ...metWeather.meta, resolution: "nearest_station_fallback" },
    };
    render(<WeatherColumn weather={fallback} citizenScience={null} />);
    expect(
      screen.getByText(/No data available — no weather station/),
    ).toBeInTheDocument();
    expect(screen.queryByText("52.3")).not.toBeInTheDocument();
  });

  it("handles a failed CS fetch (null) as the empty state", () => {
    render(<WeatherColumn weather={metWeather} citizenScience={null} />);
    expect(
      screen.getByText(
        "No citizen science weather observation submission for this Inkhundla this month.",
      ),
    ).toBeInTheDocument();
  });
});
