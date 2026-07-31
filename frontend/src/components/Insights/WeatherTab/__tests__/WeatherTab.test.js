import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import WeatherTab from "../WeatherTab";
import { api } from "../../../../lib/api";

// Alias paths do not resolve inside jest.mock — same relative form as IksTab.
jest.mock("../../../../lib/api", () => ({
  api: jest.fn(),
}));

// akvo-charts renders through ECharts, which JSDOM has no canvas for.
jest.mock("akvo-charts", () => ({
  Bar: ({ rawConfig }) => (
    <div data-testid="bar-chart" data-config={JSON.stringify(rawConfig)} />
  ),
  Line: ({ rawConfig }) => (
    <div data-testid="line-chart" data-config={JSON.stringify(rawConfig)} />
  ),
}));

const STATS = {
  key: 4588078,
  label: "Hhukwini",
  group: "Hhohho",
  value: { zone: "highveld", dclass: { category: 4, period: "2026-05" } },
  data: [
    {
      key: "precipitation_last_month",
      label: "Total precipitation last month",
      value: 39.0,
      units: "mm",
      meta: { period: "2026-05" },
    },
    {
      key: "precipitation_12m",
      label: "12-month total precipitation",
      value: 242.0,
      units: "mm",
      meta: { from: "2026-04-07", months_covered: 4 },
    },
    {
      key: "completeness_12m",
      label: "Data completeness",
      value: null,
      meta: { reason: "twg_only" },
    },
  ],
  meta: { station: "Mbabane", network: "MET", resolution: "region_station" },
};

const SERIES = {
  key: 4588078,
  label: "Hhukwini",
  group: "Hhohho",
  data: [
    {
      key: "precipitation_monthly",
      label: "Precipitation",
      units: "mm",
      data: [
        { period: "2026-04", value: 109.0 },
        { period: "2026-05", value: 39.0 },
      ],
    },
    {
      key: "temperature_monthly",
      label: "Temperature range",
      units: "°C",
      data: [
        { period: "2026-04", value: { tmax: 23.7, tmean: 17.9, tmin: 13.8 } },
        { period: "2026-05", value: null },
      ],
    },
  ],
  meta: { station: "Mbabane", network: "MET", resolution: "region_station" },
};

const NORMALS = {
  key: 4588078,
  label: "Hhukwini",
  group: "Hhohho",
  data: [
    {
      key: "precipitation_normal_30y",
      label: "30-year average",
      units: "mm",
      // Climatology: month-of-year keys, not calendar periods.
      data: [
        { period: "04", value: 51.6 },
        { period: "05", value: 22.2 },
      ],
    },
    {
      key: "temperature_normal_30y",
      label: "30-year average",
      units: "°C",
      data: [
        { period: "04", value: { tmax: 24.1, tmean: 18.7, tmin: 13.2 } },
        { period: "05", value: { tmax: 22.0, tmean: 16.8, tmin: 11.4 } },
      ],
    },
  ],
  meta: {
    definition: "monthly mean over the normals period",
    datasets: {
      precipitation: "CHIRPS 1991-2020",
      tmean: "AgERA5 1990-2020",
      tmax: "AgERA5 1990-2020",
      tmin: "AgERA5 1990-2020",
    },
    // OQ-2 closed — every normals parameter has a raster.
    unavailable: [],
  },
};

const mockApi = ({
  stats = STATS,
  series = SERIES,
  normals = NORMALS,
} = {}) => {
  api.mockImplementation((_method, url) => {
    if (url.includes("/stats")) {
      return Promise.resolve(stats);
    }
    if (url.includes("/normals")) {
      return Promise.resolve(normals);
    }
    return Promise.resolve(series);
  });
};

const renderTab = () =>
  render(
    <WeatherTab
      selectedInkhundla="Hhukwini"
      administrationId={4588078}
      region="Hhohho"
      zone="highveld"
    />,
  );

describe("WeatherTab", () => {
  it("renders header, live stat cards and both charts", async () => {
    mockApi();
    renderTab();

    await waitFor(() => {
      expect(screen.getByText("Hhukwini Inkhundla")).toBeInTheDocument();
    });
    // dclass 4 -> D3, resolved from the latest published publication
    expect(screen.getByText("D3 Extreme Drought")).toBeInTheDocument();
    expect(screen.getByText("Hhohho · Highveld")).toBeInTheDocument();

    expect(screen.getByText("39 mm")).toBeInTheDocument();
    expect(screen.getByText("242 mm")).toBeInTheDocument();
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
  });

  it("locks the completeness card for anonymous callers", async () => {
    mockApi();
    renderTab();

    await waitFor(() => {
      // Substring, so copy tweaks to the locked-card wording don't break this
      // — the assertion is about the TWG gate, not the exact sentence.
      expect(screen.getByText(/Sign in as TWG member/)).toBeInTheDocument();
    });
    expect(screen.queryByText("84%")).not.toBeInTheDocument();
  });

  it("shows the completeness value once authenticated", async () => {
    mockApi({
      stats: {
        ...STATS,
        data: STATS.data.map((d) =>
          d.key === "completeness_12m"
            ? {
                ...d,
                value: 0.84,
                meta: { window_days: 365, definition: "days_with_data" },
              }
            : d,
        ),
      },
    });
    renderTab();

    await waitFor(() => {
      expect(screen.getByText("84%")).toBeInTheDocument();
    });
  });

  it("labels the satellite card as placeholder data", async () => {
    mockApi();
    renderTab();

    await waitFor(() => {
      expect(
        screen.getByText("Difference between station and satellite"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Placeholder")).toBeInTheDocument();
  });

  it("plots station values and keeps months without data as gaps", async () => {
    mockApi();
    renderTab();

    await waitFor(() => {
      expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    });

    const bar = JSON.parse(
      screen.getByTestId("bar-chart").getAttribute("data-config"),
    );
    const station = bar.series.find((s) => s.name === "Station monthly total");
    expect(station.data).toEqual([109.0, 39.0]);

    // The 30-year average is climatology: keyed by month-of-year, so the April
    // and May series entries map onto the "04"/"05" normals, not the index.
    const normals = bar.series.find((s) => s.name === "30-year average");
    expect(normals.data).toEqual([51.6, 22.2]);

    const line = JSON.parse(
      screen.getByTestId("line-chart").getAttribute("data-config"),
    );
    const tmax = line.series.find((s) => s.name === "T max");
    expect(tmax.data).toEqual([23.7, null]);
    expect(tmax.connectNulls).toBe(false);
  });

  it("plots all six of the frame's series now every normal has a source", async () => {
    mockApi();
    renderTab();

    await waitFor(() => {
      expect(screen.getByTestId("line-chart")).toBeInTheDocument();
    });

    const line = JSON.parse(
      screen.getByTestId("line-chart").getAttribute("data-config"),
    );
    expect(line.series.map((s) => s.name)).toEqual([
      "T max",
      "T min",
      "T Mean",
      "T max 30 yr avg",
      "T min 30 yr avg",
      "T Mean 30 yr avg",
    ]);

    const average = line.series.find((s) => s.name === "T max 30 yr avg");
    // Normals are station-independent, so May carries an average even though
    // the station reported no May temperature (tmax above is [23.7, null]).
    expect(average.data).toEqual([24.1, 22.0]);
    expect(average.lineStyle.type).toBe("dashed");
    // Legend under the axis keys the observed lines only, not the averages.
    expect(line.legend.show).toBe(true);
    expect(line.legend.data).toEqual(["T max", "T min", "T Mean"]);
    // Nothing is missing, so the "unavailable" note stays off the toolbar.
    expect(screen.queryByText(/average unavailable/)).not.toBeInTheDocument();
  });

  it("hides the average for a parameter the backend reports as sourceless", async () => {
    // The contract that let tmax/tmin ship without touching this component:
    // the chart offers averages from meta.unavailable, never a fixed list.
    mockApi({
      normals: {
        ...NORMALS,
        data: [
          NORMALS.data[0],
          {
            ...NORMALS.data[1],
            data: [
              { period: "04", value: { tmax: 24.1, tmean: 18.7 } },
              { period: "05", value: { tmax: 22.0, tmean: 16.8 } },
            ],
          },
        ],
        meta: { ...NORMALS.meta, unavailable: ["tmin"] },
      },
    });
    renderTab();

    await waitFor(() => {
      expect(screen.getByTestId("line-chart")).toBeInTheDocument();
    });

    const line = JSON.parse(
      screen.getByTestId("line-chart").getAttribute("data-config"),
    );
    expect(line.series.find((s) => s.name === "T max 30 yr avg").data).toEqual([
      24.1, 22.0,
    ]);
    expect(
      line.series.find((s) => s.name === "T min 30 yr avg"),
    ).toBeUndefined();
    expect(screen.getByText("tmin average unavailable")).toBeInTheDocument();
  });

  it("still renders station data when normals are unavailable", async () => {
    mockApi({
      normals: { data: null, meta: { reason: "no_normals_extracted" } },
    });
    renderTab();

    await waitFor(() => {
      expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    });

    const bar = JSON.parse(
      screen.getByTestId("bar-chart").getAttribute("data-config"),
    );
    expect(bar.series.map((s) => s.name)).toEqual(["Station monthly total"]);
  });

  it("surfaces the nearest-station fallback rather than passing it off as local", async () => {
    mockApi({
      series: {
        ...SERIES,
        meta: {
          station: "Mbabane",
          resolution: "nearest_station_fallback",
          station_region: "Hhohho",
          distance_km: 28.4,
        },
      },
    });
    renderTab();

    await waitFor(() => {
      expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    });
    expect(
      screen.getAllByText(/Nearest station: Mbabane \(Hhohho\) · 28.4 km away/)
        .length,
    ).toBeGreaterThan(0);
  });

  it("reports no data instead of an empty chart when no station covers the period", async () => {
    mockApi({
      stats: {
        ...STATS,
        data: null,
        meta: { reason: "no_station_data_for_period" },
      },
      series: {
        ...SERIES,
        data: null,
        meta: { reason: "no_station_data_for_period" },
      },
    });
    renderTab();

    await waitFor(() => {
      expect(screen.getByText("No data available")).toBeInTheDocument();
    });
    // Header context survives the no-data case.
    expect(screen.getByText("Hhukwini Inkhundla")).toBeInTheDocument();
    expect(screen.queryByTestId("bar-chart")).not.toBeInTheDocument();
    expect(
      screen.getAllByText("No station data available for this period").length,
    ).toBe(2);
  });
});
