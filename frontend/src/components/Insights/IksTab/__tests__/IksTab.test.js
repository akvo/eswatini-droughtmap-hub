import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import IksTab from "../IksTab";
import { api } from "../../../../lib/api";

// Mock the API wrapper
jest.mock("../../../../lib/api", () => ({
  api: jest.fn(),
}));

// Mock akvo-charts to avoid canvas/DOM errors in jsdom during test run
jest.mock("akvo-charts", () => ({
  Line: ({ rawConfig }) => (
    <div data-testid="line-chart" data-config={JSON.stringify(rawConfig)}>
      Line Chart Mock
    </div>
  ),
}));

const mockIndicators = [
  { id: 1, name: "1__bs___blue_swallows_appearance__tinkon" },
  { id: 9, name: "9__f___frogs_calling_singing__emacoco_ak" },
];

// Mock matchMedia for Ant Design responsiveness tests in JSDOM
beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: jest.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
});

const mockNetSignal = {
  weeks: ["May 01", "May 08"],
  trend: {
    Hhohho: [2.0, 1.4],
    Manzini: [1.5, 1.22],
    Lubombo: [1.82, 1.0],
    Shiselweni: [2.07, 1.0],
  },
};

const mockCounts = {
  radar_labels: ["Frogs", "Southern Ground-Hornbill"],
  radar: {
    Hhohho: [60.5, 57.9],
    Manzini: [67.1, 67.5],
  },
};

const mockAgreement = {
  agreement: [
    {
      name: "Hhukwini",
      region: "Hhohho",
      iks: 65.9,
      sat: 16.7,
      agreement: "contested",
    },
    {
      name: "Lobamba",
      region: "Hhohho",
      iks: 70.3,
      sat: 16.7,
      agreement: "contested",
    },
  ],
};

const mockHeatmap = {
  constituencies: ["Hhukwini", "Lobamba"],
  weeks: ["May 01", "May 08"],
  heatmap: [
    [1, 5],
    [2, 4],
  ],
};

describe("IksTab Component", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders spin loading state initially", () => {
    // Make api promise pending
    api.mockImplementation(() => new Promise(() => {}));
    render(<IksTab />);
    expect(
      screen.getByText("Fetching Indigenous Knowledge data..."),
    ).toBeInTheDocument();
  });

  it("renders error state when api fails", async () => {
    api.mockRejectedValue(new Error("Network failure"));
    render(<IksTab />);
    await waitFor(() => {
      expect(screen.getByText("Failed to Load IKS Data")).toBeInTheDocument();
      expect(screen.getByText("Network failure")).toBeInTheDocument();
    });
  });

  it("renders empty state when data is empty", async () => {
    api.mockImplementation((method, url) => {
      if (url === "/iks/indicators") return Promise.resolve([]);
      if (url === "/iks/aggregations/net-signal")
        return Promise.resolve({ weeks: [], trend: {} });
      return Promise.resolve(null);
    });

    render(<IksTab />);
    await waitFor(() => {
      expect(
        screen.getByText("No submissions yet for this season."),
      ).toBeInTheDocument();
    });
  });

  it("renders data views successfully (trend line chart, catalogue table, heatmap)", async () => {
    api.mockImplementation((method, url) => {
      if (url === "/iks/indicators") return Promise.resolve(mockIndicators);
      if (url === "/iks/aggregations/net-signal")
        return Promise.resolve(mockNetSignal);
      if (url === "/iks/aggregations/indicator-counts")
        return Promise.resolve(mockCounts);
      if (url === "/iks/aggregations/agreement")
        return Promise.resolve(mockAgreement);
      if (url === "/iks/aggregations/heatmap")
        return Promise.resolve(mockHeatmap);
      return Promise.resolve(null);
    });

    render(<IksTab />);

    // 1. Verify trend line chart renders and has the correct region colors
    await waitFor(() => {
      const chartMock = screen.getByTestId("line-chart");
      expect(chartMock).toBeInTheDocument();
      const configStr = chartMock.getAttribute("data-config");
      const config = JSON.parse(configStr);

      // Verify the 4 region series colors are present in line chart config
      const hhohhoSeries = config.series.find((s) => s.name === "Hhohho");
      expect(hhohhoSeries.itemStyle.color).toBe("#3E5EB9");

      const manziniSeries = config.series.find((s) => s.name === "Manzini");
      expect(manziniSeries.itemStyle.color).toBe("#2E8B57");
    });

    // 2. Verify indicator catalogue table renders headers and indicator rows
    expect(screen.getByText("IKS Indicators Catalogue")).toBeInTheDocument();
    expect(
      screen.getByText("1. BS – Blue Swallows appearance"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("9. F – Frogs calling/singing"),
    ).toBeInTheDocument();

    // Verify submission count mappings (Frogs count: Hhohho 60.5 + Manzini 67.1 = 128)
    expect(screen.getByText("128")).toBeInTheDocument();

    // 3. Verify deferred heatmap mounts
    await waitFor(() => {
      expect(
        screen.getByText("Constituency × Week Submission Heatmap"),
      ).toBeInTheDocument();
    });
  });
});
