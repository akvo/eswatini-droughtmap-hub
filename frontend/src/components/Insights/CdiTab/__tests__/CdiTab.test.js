import { render, screen, waitFor, within } from "@testing-library/react";
import React from "react";
import CdiTab from "../CdiTab";
import { api } from "../../../../lib/api";

jest.mock("../../../../lib/api", () => ({
  api: jest.fn(),
}));

jest.mock("akvo-charts", () => ({
  Bar: ({ rawConfig }) => (
    <div data-testid="bar-chart" data-config={JSON.stringify(rawConfig)} />
  ),
  Line: ({ rawConfig }) => (
    <div data-testid="line-chart" data-config={JSON.stringify(rawConfig)} />
  ),
}));

const card = (key, value, meta) => ({
  key,
  label: `${key.toUpperCase()} percentile rank`,
  value,
  units: "pct_rank",
  meta,
});

const STATS = {
  key: 4588078,
  label: "Mhlangatane",
  group: "Hhohho",
  value: { zone: "highveld", dclass: { category: 4, period: "2026-05" } },
  data: [
    card("spi", 0.05, {
      period: "2026-05",
      previous: 0.22,
      previous_period: "2026-04",
      change_pct: -77.3,
    }),
    card("evi2", 0.26, {
      period: "2026-05",
      previous: 0.5,
      previous_period: "2026-04",
      change_pct: -48,
    }),
    card("esi", null, {
      period: "2026-05",
      previous: null,
      previous_period: null,
      change_pct: null,
      reason: "no_raster_data",
    }),
    card("sm", 0.05, {
      period: "2026-05",
      previous: 0.22,
      previous_period: "2026-04",
      change_pct: -77.3,
    }),
  ],
  breakdown: {
    group: "dclass_history",
    data: [
      { period: "2025-12", value: 3 },
      { period: "2026-01", value: null },
      { period: "2026-02", value: -9999 },
      { period: "2026-05", value: 4 },
    ],
  },
  meta: { period: "2026-05", from: "2025-12", to: "2026-05", months: 4 },
};

const series = (key) => ({
  key: 4588078,
  label: "Mhlangatane",
  group: "Hhohho",
  data: [
    {
      key,
      label: `${key.toUpperCase()} percentile rank`,
      units: "pct_rank",
      data: [
        { period: "2025-12", value: 0.41 },
        { period: "2026-01", value: null },
      ],
    },
  ],
  meta: { from: "2025-12", to: "2026-01", months: 2, indicators: [key] },
});

const route = (url) => {
  if (url.includes("/stats")) {
    return Promise.resolve(STATS);
  }
  const key = new URL(`http://x${url}`).searchParams.get("indicators");
  return Promise.resolve(series(key));
};

const renderTab = () =>
  render(
    <CdiTab
      selectedInkhundla="Mhlangatane"
      administrationId={4588078}
      region="Hhohho"
      zone="highveld"
    />,
  );

describe("CdiTab", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    api.mockImplementation((_method, url) => route(url));
  });

  it("fetches stats once and one series per chart, each narrowed to its index", async () => {
    renderTab();
    await waitFor(() =>
      expect(
        screen.getByText("D-class classification history"),
      ).toBeInTheDocument(),
    );

    const urls = api.mock.calls.map(([, url]) => url);
    // One /stats — the whole point of the split: the strip and all four cards
    // come from a single call, replacing INS-1's per-month fan-out.
    expect(urls.filter((u) => u.includes("/stats"))).toHaveLength(1);
    // and one /series per chart, each asking for only its own index
    ["spi", "evi2", "esi", "sm"].forEach((key) => {
      expect(
        urls.filter(
          (u) => u.includes("/series") && u.includes(`indicators=${key}`),
        ),
      ).toHaveLength(1);
    });
  });

  it("opens on a trailing window ending at LAST month, never the current one", async () => {
    // Computed independently of lastNMonths (which has its own unit tests) so
    // this pins the wiring, not the helper.
    const first = new Date();
    first.setDate(1);
    const period = (offset) => {
      const d = new Date(first.getFullYear(), first.getMonth() + offset, 1);
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    };

    renderTab();
    await waitFor(() => expect(api).toHaveBeenCalled());

    const seriesUrls = api.mock.calls
      .map(([, url]) => url)
      .filter((u) => u.includes("/series"));
    expect(seriesUrls.length).toBeGreaterThan(0);
    seriesUrls.forEach((url) => {
      // 12 inclusive months ending last month: an in-progress month would
      // draw a partial bar that reads as a collapse.
      expect(url).toContain(`from=${period(-12)}`);
      expect(url).toContain(`to=${period(-1)}`);
      expect(url).not.toContain(`to=${period(0)}`);
    });
  });

  it("renders the header chip from the published D-class", async () => {
    renderTab();
    await waitFor(() =>
      expect(screen.getByText("Mhlangatane Inkhundla")).toBeInTheDocument(),
    );
    expect(screen.getByText("Hhohho · Highveld")).toBeInTheDocument();
    // "D3" is also a strip cell here, so scope to the header row rather than
    // asserting globally.
    const header = screen
      .getByText("Mhlangatane Inkhundla")
      .closest("div").parentElement;
    expect(within(header).getByText("D3")).toBeInTheDocument();
  });

  it("renders one strip cell per month, including gaps and No-data output", async () => {
    renderTab();
    await waitFor(() =>
      expect(screen.getByText("Dec 2025")).toBeInTheDocument(),
    );
    // 4 periods in the fixture: a class, a null gap, a -9999, a class
    ["Dec 2025", "Jan 2026", "Feb 2026", "May 2026"].forEach((label) => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
    expect(screen.getByText("D2")).toBeInTheDocument();
    // null (no publication / no decision) and -9999 (CDI had no signal) both
    // collapse to one empty cell — same as the IKS strips
    expect(screen.getAllByText("-")).toHaveLength(2);
    // and the legend names that state for this tab
    expect(screen.getByText("No data")).toBeInTheDocument();
  });

  it("shows the actual published period on the cards, not 'last month'", async () => {
    renderTab();
    await waitFor(() =>
      expect(screen.getByText("Precipitation")).toBeInTheDocument(),
    );
    expect(screen.getAllByText(/May 2026 · prev 0\.22/).length).toBeGreaterThan(
      0,
    );
    expect(screen.queryByText(/Last month's/i)).not.toBeInTheDocument();
  });

  it("renders an em dash and a reason when an index has no raster", async () => {
    renderTab();
    await waitFor(() =>
      expect(screen.getByText("Land surface temperature")).toBeInTheDocument(),
    );
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(
      screen.getByText("No published value for this month"),
    ).toBeInTheDocument();
  });

  it("draws precipitation as bars and the rest as lines, on a pinned 0-1 axis", async () => {
    renderTab();
    await waitFor(() =>
      expect(screen.getByTestId("bar-chart")).toBeInTheDocument(),
    );
    expect(screen.getAllByTestId("line-chart")).toHaveLength(3);

    const config = JSON.parse(
      screen.getByTestId("bar-chart").getAttribute("data-config"),
    );
    // Percentile ranks are 0-1 by definition — an auto-scaled axis would make
    // a flat month look like a dramatic swing.
    expect(config.yAxis.min).toBe(0);
    expect(config.yAxis.max).toBe(1);
    expect(config.series[0].data).toEqual([0.41, null]);
  });

  it("still renders the header when nothing is published", async () => {
    api.mockImplementation((_method, url) =>
      url.includes("/stats")
        ? Promise.resolve({
            key: 4588078,
            label: "Mhlangatane",
            group: "Hhohho",
            value: { zone: "highveld", dclass: null },
            data: null,
            breakdown: null,
            meta: { reason: "no_published_data" },
          })
        : Promise.resolve(series("spi")),
    );
    renderTab();

    await waitFor(() =>
      expect(screen.getByText("Mhlangatane Inkhundla")).toBeInTheDocument(),
    );
    expect(screen.getByText("No data available")).toBeInTheDocument();
    // no strip, no cards, no charts to draw
    expect(
      screen.queryByText("D-class classification history"),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("bar-chart")).not.toBeInTheDocument();
  });
});
