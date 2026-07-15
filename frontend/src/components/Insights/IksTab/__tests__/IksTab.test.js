import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import IksTab from "../IksTab";
import { api } from "../../../../lib/api";

// Mock the API wrapper
jest.mock("../../../../lib/api", () => ({
  api: jest.fn(),
}));

// Mock akvo-charts to avoid JSDOM canvas issues
jest.mock("akvo-charts", () => ({
  Line: ({ rawConfig }) => (
    <div data-testid="line-chart" data-config={JSON.stringify(rawConfig)}>
      Line Chart Mock
    </div>
  ),
}));

const mockNetSignal = {
  weeks: ["May 01", "May 08"],
  trend: {
    Hhohho: [2.0, 1.4],
  },
};

const mockSoilTrend = {
  weeks: ["May 01", "May 08"],
  soil_trend: {
    dry: [18.6, 22.0],
  },
};

const mockIndicators = [
  { id: 1, name: "1__bs___blue_swallows_appearance__tinkon" },
];

// Mock matchMedia for Ant Design responsiveness in JSDOM tests
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

describe("IksTab Component Redesigned Mockup", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders spin loading state initially", () => {
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
    });
  });

  it("renders layout successfully mapping figma mockup elements", async () => {
    api.mockImplementation((method, url) => {
      if (url === "/iks/indicators") return Promise.resolve(mockIndicators);
      if (url === "/iks/aggregations/net-signal")
        return Promise.resolve(mockNetSignal);
      if (url === "/iks/aggregations/soil-trend")
        return Promise.resolve(mockSoilTrend);
      if (url === "/iks/aggregations/indicator-counts")
        return Promise.resolve({ data: [] });
      if (url === "/iks/aggregations/agreement")
        return Promise.resolve({ weeks: [], regions: {} });
      if (url === "/iks/aggregations/heatmap") return Promise.resolve({});
      if (url === "/iks/1/stats")
        return Promise.resolve({
          total_reports_received: 10,
          total_months_drought: 3,
          reporting_consistency_percentage: 95.5,
          validation_rate_percentage: 88.0,
          average_validation_time_days: 1.2,
          form_completion_percentage: 82.0,
          zone: "highveld",
          indicator_activity: {
            months: ["2025-08", "2025-09"],
            rain_leaning: [2, 3],
            extreme_weather: [1, 0],
          },
        });
      if (url === "/iks/1/series?bulk=true")
        return Promise.resolve({
          months: ["2025-08", "2025-09"],
          indicators: {
            "1__bs___blue_swallows_appearance__tinkon": [true, false],
          },
        });
      if (url === "/iks/1/photos")
        return Promise.resolve({
          photos: [
            {
              title: "Test Photo",
              date: "Aug 25",
              url: "http://example.com/test.jpg",
            },
          ],
        });
      return Promise.resolve(null);
    });

    render(<IksTab administrationId={1} selectedInkhundla="Mhlangatane" />);

    // 1. Verify Header
    await waitFor(() => {
      expect(screen.getByText("Mhlangatane Inkhundla")).toBeInTheDocument();
    });

    // 2. Verify KPI Panels
    expect(screen.getByText("Reporting consistency")).toBeInTheDocument();
    expect(screen.getByText("95.5%")).toBeInTheDocument();
    expect(screen.getByText("Form completion")).toBeInTheDocument();
    expect(screen.getByText("82%")).toBeInTheDocument();

    // 3. Verify Soil grids and Accordions
    expect(
      screen.getByText("Soil moisture (Womile / Ubutsile / Umanti)"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Section B: Rainfall predictors (21 indicators)"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Section C: Seasonal & extreme-weather predictors (8 indicators)",
      ),
    ).toBeInTheDocument();

    // 4. Verify Photo attachments block
    expect(screen.getByText("Submitted photos")).toBeInTheDocument();
    expect(screen.getByText("Test Photo")).toBeInTheDocument();
  });

  it("handles null administrationId without calling admin endpoints", async () => {
    api.mockImplementation((method, url) => {
      if (url === "/iks/indicators") return Promise.resolve(mockIndicators);
      if (url === "/iks/aggregations/net-signal")
        return Promise.resolve(mockNetSignal);
      if (url === "/iks/aggregations/soil-trend")
        return Promise.resolve(mockSoilTrend);
      if (url === "/iks/aggregations/indicator-counts")
        return Promise.resolve({ data: [] });
      if (url === "/iks/aggregations/agreement")
        return Promise.resolve({ weeks: [], regions: {} });
      if (url === "/iks/aggregations/heatmap") return Promise.resolve({});
      return Promise.resolve(null);
    });

    render(<IksTab administrationId={null} selectedInkhundla="Mhlangatane" />);

    await waitFor(() => {
      expect(screen.getByText("Mhlangatane Inkhundla")).toBeInTheDocument();
    });

    // Verify admin stats/series calls were not triggered, but page still rendered
    expect(api).not.toHaveBeenCalledWith("GET", "/iks/null/stats");
    expect(api).not.toHaveBeenCalledWith("GET", "/iks/null/series?bulk=true");
  });

  it("renders empty fallback when photos are empty", async () => {
    api.mockImplementation((method, url) => {
      if (url === "/iks/indicators") return Promise.resolve(mockIndicators);
      if (url === "/iks/aggregations/net-signal")
        return Promise.resolve(mockNetSignal);
      if (url === "/iks/aggregations/soil-trend")
        return Promise.resolve(mockSoilTrend);
      if (url === "/iks/aggregations/indicator-counts")
        return Promise.resolve({ data: [] });
      if (url === "/iks/aggregations/agreement")
        return Promise.resolve({ weeks: [], regions: {} });
      if (url === "/iks/aggregations/heatmap") return Promise.resolve({});
      if (url === "/iks/1/stats")
        return Promise.resolve({
          total_reports_received: 0,
          total_months_drought: 0,
          reporting_consistency_percentage: 0.0,
          validation_rate_percentage: 0.0,
          average_validation_time_days: 0.0,
          form_completion_percentage: 0.0,
          zone: "highveld",
          indicator_activity: {
            months: [],
            rain_leaning: [],
            extreme_weather: [],
          },
        });
      if (url === "/iks/1/series?bulk=true")
        return Promise.resolve({ months: [], indicators: {} });
      if (url === "/iks/1/photos") return Promise.resolve({ photos: [] });
      return Promise.resolve(null);
    });

    render(<IksTab administrationId={1} selectedInkhundla="Mhlangatane" />);

    await waitFor(() => {
      expect(screen.getByText("No photos submitted")).toBeInTheDocument();
    });
  });
});
