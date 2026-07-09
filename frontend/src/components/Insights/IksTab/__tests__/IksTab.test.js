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
      return Promise.resolve(null);
    });

    render(<IksTab />);

    // 1. Verify Header
    await waitFor(() => {
      expect(screen.getByText("Mhlangatane Inkhundla")).toBeInTheDocument();
    });

    // 2. Verify KPI Panels
    expect(screen.getByText("Reporting consistency")).toBeInTheDocument();
    expect(screen.getByText("Validation rate")).toBeInTheDocument();
    expect(screen.getByText("Avg. validation time")).toBeInTheDocument();
    expect(screen.getByText("Form completion")).toBeInTheDocument();

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
  });
});
