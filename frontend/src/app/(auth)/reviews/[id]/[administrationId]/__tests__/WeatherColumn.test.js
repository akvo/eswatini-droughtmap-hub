import { render, screen } from "@testing-library/react";
import { WeatherColumn } from "../IndividualReview";

const metWeather = {
  data: [
    { key: "min_temperature", label: "Min temperature", value: 12, units: "°C" },
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
    { key: "precipitation", label: "Precipitation (monthly)", value: 55, units: "mm" },
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
    expect(screen.getByText("Met Office: Mbabane")).toBeInTheDocument();
    expect(
      screen.getByText("Citizen science: Big Bend Community"),
    ).toBeInTheDocument();
    expect(screen.getByText("55")).toBeInTheDocument();
    expect(screen.getByText("pending sensor")).toBeInTheDocument();
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
        "No citizen-science submission for this Inkhundla this month.",
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
      screen.getByText("Citizen science: Big Bend Community"),
    ).toBeInTheDocument();
  });

  it("handles a failed CS fetch (null) as the empty state", () => {
    render(<WeatherColumn weather={metWeather} citizenScience={null} />);
    expect(
      screen.getByText(
        "No citizen-science submission for this Inkhundla this month.",
      ),
    ).toBeInTheDocument();
  });
});
