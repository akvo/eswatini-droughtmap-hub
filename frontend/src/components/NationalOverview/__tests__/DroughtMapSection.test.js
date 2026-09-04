import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import DroughtMapSection from "../DroughtMapSection";

const mockApi = jest.fn(() => Promise.resolve({}));
jest.mock("@/lib", () => ({
  api: (...args) => mockApi(...args),
}));

jest.mock("@/context/PrintContextProvider", () => ({
  usePrintContext: () => ({}),
}));

// antd's Select emits a CSS-in-JS selector jsdom cannot parse
// (":scope +.ant-select-item-option-selected:not(...))+..."), which throws
// during commit. A native <select> stands in — and doubles as the handle for
// driving a month change, which antd's listbox does not expose in jsdom.
jest.mock("antd", () => {
  const antd = jest.requireActual("antd");
  const MockSelect = ({ value, onChange, options = [], className }) => (
    <select
      data-testid={className?.includes("select-styled") ? "month" : "other"}
      value={value}
      onChange={(e) => onChange?.(Number(e.target.value))}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
  return { ...antd, Select: MockSelect };
});

// The maps need a DOM Leaflet cannot have in jsdom. The Inkhundla callback is
// the part this suite drives, so the mock exposes it as a button.
jest.mock("../OverviewMap", () => {
  const MockOverviewMap = ({ onInkhundlaSelect }) => (
    <button
      data-testid="select-inkhundla"
      onClick={() => onInkhundlaSelect?.(42, "Mhlume")}
    >
      map
    </button>
  );
  return MockOverviewMap;
});
jest.mock("../LayerMap", () => {
  const MockLayerMap = () => <div data-testid="layer-map" />;
  return MockLayerMap;
});

// ECharts paints to a canvas jsdom does not implement, and fails from a
// requestAnimationFrame callback after the test has finished. The card's
// numbers are the subject here, not its sparkline.
jest.mock("../MiniDonutChart", () => {
  const MockDonut = () => <div data-testid="donut" />;
  return MockDonut;
});
jest.mock("../MiniBarChart", () => {
  const MockBars = () => <div data-testid="bars" />;
  return MockBars;
});

const DATES = [
  { value: 10, label: "2026-05-01" },
  { value: 9, label: "2026-04-01" },
];

const METRICS = {
  period: "2026-05",
  periodLabel: "May 2026",
  rainfall: { value: -18.3, unit: "mm", note: "May 2026 deviation" },
  temperature: { value: null, unit: "°C", note: "May 2026 deviation" },
  activeStations: { online: 3, total: 3, onlinePct: 100, note: "as of May" },
  fieldReports: { count: 20, note: "in May 2026" },
};

const renderSection = (props = {}) =>
  render(
    <DroughtMapSection
      mapId={10}
      dates={DATES}
      validatedValues={[]}
      metrics={METRICS}
      {...props}
    />,
  );

const metricsCalls = () =>
  mockApi.mock.calls.filter(([, url]) => url.startsWith("/insights/metrics"));

describe("DroughtMapSection metrics anchoring", () => {
  beforeEach(() => {
    mockApi.mockClear();
    mockApi.mockResolvedValue({});
  });

  it("does not refetch the month the server already rendered", async () => {
    renderSection();
    // The SSR payload IS the latest published month, so a request here would
    // be a duplicate and a flash of changed numbers (KPI-1 D-10).
    await waitFor(() => expect(screen.getByTestId("select-inkhundla")));
    expect(metricsCalls()).toHaveLength(0);
  });

  it("carries the selected month when an Inkhundla is picked", async () => {
    renderSection();
    fireEvent.click(screen.getByTestId("select-inkhundla"));

    await waitFor(() => expect(metricsCalls()).toHaveLength(1));
    const [, url] = metricsCalls()[0];
    // Both filters, one request — the month must not be dropped when the
    // Inkhundla changes (KPI-1 FR-4).
    expect(url).toContain("year_month=2026-05");
    expect(url).toContain("inkhundla_id=42");
  });

  it("refetches every card when the month changes", async () => {
    renderSection();
    // The selector drove the map and left the cards on whatever month the
    // server had rendered (KPI-1 FR-3).
    fireEvent.change(screen.getAllByTestId("month")[0], {
      target: { value: "9" },
    });

    await waitFor(() => expect(metricsCalls()).toHaveLength(1));
    expect(metricsCalls()[0][1]).toContain("year_month=2026-04");
  });

  it("renders an em dash rather than 0 for a missing deviation", () => {
    renderSection();
    // 0 mm is a real reading — "bang on the 30-year normal" — and must stay
    // distinguishable from "this month has no observation" (KPI-1 NFR-1).
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders the field-report note from the API, not a fixed 30 days", () => {
    renderSection();
    expect(screen.getByText("in May 2026")).toBeInTheDocument();
    expect(screen.queryByText(/last 30 days/i)).not.toBeInTheDocument();
  });
});
