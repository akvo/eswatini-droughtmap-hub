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
  // Shaped exactly like GET /api/v1/risk-levels/{administration_id} (RL-2).
  const mockRiskData = {
    period: "2026-05",
    administration: {
      id: 1,
      name: "Nkwene",
      region: "Shiselweni",
      zone: "lower_middleveld",
    },
    rank: 7,
    drought: {
      key: "D3",
      value: 0.8,
      trend: "stable",
      trend_desc: "1 month unchanged",
      confidence: {
        band: null,
        value: null,
        meta: { reason: "no_station_baseline" },
      },
    },
    exposure: {
      value: 0.4474,
      data: [
        {
          key: "land_use_dvi_agri",
          value: 0.61,
          unit: null,
          norm: 0.09,
          scored: true,
        },
        {
          key: "population",
          value: 8956,
          unit: "people",
          norm: 0.82,
          scored: true,
        },
        { key: "cattle", value: 1364, unit: "head", norm: 0.4, scored: true },
        {
          key: "water_demand",
          value: null,
          unit: "m3",
          norm: null,
          scored: true,
          meta: { unit_status: "assumed_pending_dwa" },
        },
        {
          key: "under_five",
          value: 184,
          unit: "children",
          norm: null,
          scored: false,
        },
        {
          key: "rainfed_cropland",
          value: 1069,
          unit: "ha",
          norm: null,
          scored: false,
        },
      ],
      unavailable: ["water_demand"],
    },
    vulnerability: {
      value: 0.6,
      data: [
        { key: "ipc_phase", value: 3, format: "ipc", scored: true },
        {
          key: "people_per_water_point",
          value: 2239,
          unit: "people/point",
          scored: false,
          meta: { basis: "population / (boreholes + taps)" },
        },
      ],
    },
    risk_score: {
      value: 0.2387,
      class: "Moderate",
      meta: {
        band: "watch",
        scale: [0, 1],
        band_thresholds: { urgent: 0.5, watch: 0.15, monitor: 0.0 },
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

  it("renders the drought cycle and trend from the payload", () => {
    render(<RiskScoreBuildUp riskData={mockRiskData} />);

    expect(screen.getByText("Validated drought score")).toBeInTheDocument();
    expect(
      screen.getByText("Signed off in 2026-05 review cycle"),
    ).toBeInTheDocument();
    expect(screen.getByText("■ STABLE")).toBeInTheDocument();
    expect(screen.getByText("1 month unchanged")).toBeInTheDocument();
  });

  it("renders confidence as an empty state, never a fabricated band", () => {
    render(<RiskScoreBuildUp riskData={mockRiskData} />);

    expect(screen.getByText("— —")).toBeInTheDocument();
    expect(
      screen.getByText("Awaiting weather-station baseline"),
    ).toBeInTheDocument();
    expect(screen.queryByText("High")).not.toBeInTheDocument();
  });

  it("renders a confidence band when the API ever sends one", () => {
    const withConfidence = {
      ...mockRiskData,
      drought: { ...mockRiskData.drought, confidence: { band: "high" } },
    };
    render(<RiskScoreBuildUp riskData={withConfidence} />);

    expect(screen.getByText("High")).toBeInTheDocument();
  });

  it("renders exposure absolutes with the unit the API declares", () => {
    render(<RiskScoreBuildUp riskData={mockRiskData} />);

    expect(screen.getByText("8,956 people")).toBeInTheDocument();
    expect(screen.getByText("1,364 head")).toBeInTheDocument();
    expect(screen.getByText("184 children")).toBeInTheDocument();
    expect(screen.getByText("1,069 ha")).toBeInTheDocument();
    // water_demand is null -> N/A, and its m3 unit is never converted here.
    expect(screen.getByText("Water demand")).toBeInTheDocument();
    expect(screen.queryByText(/ L$/)).not.toBeInTheDocument();
  });

  it("marks unscored rows as context so they cannot read as inputs", () => {
    render(<RiskScoreBuildUp riskData={mockRiskData} />);

    // under_five, rainfed_cropland, people_per_water_point
    expect(screen.getAllByText("CONTEXT")).toHaveLength(3);
  });

  it("renders the IPC phase and the water-access context row", () => {
    render(<RiskScoreBuildUp riskData={mockRiskData} />);

    expect(screen.getByText("Susceptibility")).toBeInTheDocument();
    expect(screen.getByText("Phase 3: Crisis")).toBeInTheDocument();

    expect(screen.getByText("Water access pressure")).toBeInTheDocument();
    expect(screen.getByText("2,239 people/point")).toBeInTheDocument();

    // Dropped by the methodology (redesign D-7) — must not reappear.
    expect(screen.queryByText("Preparedness index")).not.toBeInTheDocument();
  });

  it("displays the 0-1 API score as the 0-10 headline", () => {
    render(<RiskScoreBuildUp riskData={mockRiskData} />);

    expect(screen.getByText("2.4")).toBeInTheDocument();
  });

  it("scales an urgent score the same way", () => {
    const urgentData = {
      ...mockRiskData,
      risk_score: { ...mockRiskData.risk_score, value: 0.52, band: "urgent" },
    };
    render(<RiskScoreBuildUp riskData={urgentData} />);

    expect(screen.getByText("5.2")).toBeInTheDocument();
  });

  it("renders N/A instead of a confident zero when unscored", () => {
    const unscored = {
      ...mockRiskData,
      exposure: { ...mockRiskData.exposure, value: null },
      vulnerability: { value: null, data: [] },
      risk_score: {
        value: null,
        class: null,
        meta: { ...mockRiskData.risk_score.meta, band: null },
      },
    };
    render(<RiskScoreBuildUp riskData={unscored} />);

    expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);
    expect(screen.queryByText("0.0")).not.toBeInTheDocument();
  });

  it("renders placeholder text when riskData is not provided", () => {
    render(<RiskScoreBuildUp riskData={null} />);
    expect(
      screen.getByText("No risk assessment data available for this area."),
    ).toBeInTheDocument();
  });
});
