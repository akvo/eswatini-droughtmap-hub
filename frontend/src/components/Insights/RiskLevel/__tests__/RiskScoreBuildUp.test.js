import { render, screen } from "@testing-library/react";
import RiskScoreBuildUp from "../RiskScoreBuildUp";

// Mock matchMedia for Ant Design Collapse component
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

describe("RiskScoreBuildUp", () => {
  const mockRiskData = {
    period: "2026-05",
    administration: {
      id: 1,
      name: "Nkwene",
      region: "Shiselweni",
      zone: "Middleveld",
    },
    drought: {
      key: "D3",
      label: "D3 — Extreme Drought",
      value: 0.8,
      trend: "stable",
      trend_delta: 0,
      confidence: "high",
    },
    exposure: {
      value: 0.4474,
      data: [
        { key: "population", value: 8956 },
        { key: "u5", value: 184 },
        { key: "rainfed_ha", value: 1069 },
        { key: "livestock", value: 1364 },
        { key: "water_demand_liters", value: null },
      ],
    },
    vulnerability: {
      value: 0.667,
      data: [
        { key: "v_water", value: 1.0 },
        { key: "v_ipc", value: 0.534 },
        { key: "v_prep", value: 0.467 },
      ],
    },
    risk_score: {
      value: 2.39,
      meta: {
        band: "monitor",
        band_thresholds: { urgent: 4.5, watch: 2.5 },
      },
    },
  };

  it("renders the component headers and default accordion panels", () => {
    render(<RiskScoreBuildUp riskData={mockRiskData} />);

    expect(screen.getByText("Risk score build-up")).toBeInTheDocument();
    expect(screen.getByText("Drought")).toBeInTheDocument();
    expect(screen.getByText("Exposure")).toBeInTheDocument();
    expect(screen.getByText("Vulnerability")).toBeInTheDocument();
  });

  it("renders drought category, stable trend status, and confidence label", () => {
    render(<RiskScoreBuildUp riskData={mockRiskData} />);

    expect(screen.getByText("D3 — Extreme Drought")).toBeInTheDocument();
    expect(screen.getByText("Stable")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
  });

  it("renders exposure metrics correctly with formatting", () => {
    render(<RiskScoreBuildUp riskData={mockRiskData} />);

    expect(screen.getByText("8,956 people")).toBeInTheDocument();
    expect(screen.getByText("184 children")).toBeInTheDocument();
    expect(screen.getByText("1,069 ha rain-fed")).toBeInTheDocument();
    expect(screen.getByText("1,364 head")).toBeInTheDocument();
    // water_demand is null, so it should display "N/A"
    expect(screen.getByText("Water demand:")).toBeInTheDocument();
  });

  it("renders vulnerability index values and mapped IPC Phase", () => {
    render(<RiskScoreBuildUp riskData={mockRiskData} />);

    expect(screen.getByText("Water access pressure:")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
    
    expect(screen.getByText("Susceptibility:")).toBeInTheDocument();
    // v_ipc = 0.534 maps to Phase 3: Crisis
    expect(screen.getByText("Phase 3: Crisis")).toBeInTheDocument();

    expect(screen.getByText("Preparedness index:")).toBeInTheDocument();
    expect(screen.getByText("47%")).toBeInTheDocument();
  });

  it("displays the correct band label and formatted final score", () => {
    render(<RiskScoreBuildUp riskData={mockRiskData} />);

    expect(screen.getByText("Routine monitoring")).toBeInTheDocument();
    expect(screen.getByText("2.39 / 10")).toBeInTheDocument();
  });

  it("renders watch list band for watch list score", () => {
    const watchData = {
      ...mockRiskData,
      risk_score: {
        value: 3.10,
        meta: {
          band: "watch",
          band_thresholds: { urgent: 4.5, watch: 2.5 },
        },
      },
    };
    render(<RiskScoreBuildUp riskData={watchData} />);

    expect(screen.getByText("Watch list")).toBeInTheDocument();
    expect(screen.getByText("3.10 / 10")).toBeInTheDocument();
  });

  it("renders urgent response required band for urgent score", () => {
    const urgentData = {
      ...mockRiskData,
      risk_score: {
        value: 5.20,
        meta: {
          band: "urgent",
          band_thresholds: { urgent: 4.5, watch: 2.5 },
        },
      },
    };
    render(<RiskScoreBuildUp riskData={urgentData} />);

    expect(screen.getByText("Urgent response required")).toBeInTheDocument();
    expect(screen.getByText("5.20 / 10")).toBeInTheDocument();
  });

  it("renders placeholder text when riskData is not provided", () => {
    render(<RiskScoreBuildUp riskData={null} />);
    expect(
      screen.getByText("No risk assessment data available for this area.")
    ).toBeInTheDocument();
  });
});
