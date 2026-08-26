import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import RiskLevelPage from "../../../../app/detailed-insights/risk-level/page";
import { api } from "@/lib/api";
import { useInsights } from "@/context/InsightsContextProvider";
import { ACTIVITY_STATUS } from "@/static/config";

// Mock next/dynamic to load RiskLevelTab synchronously in test environment
jest.mock("next/dynamic", () => () => {
  return require("../RiskLevelTab").default;
});

// Mock the api module
jest.mock("@/lib/api", () => ({
  api: jest.fn(),
}));

// Mock useInsights hook
jest.mock("@/context/InsightsContextProvider", () => ({
  useInsights: jest.fn(),
}));

// Mock the nested components to simplify integration tests
jest.mock("../RiskScoreBuildUp", () => {
  return function MockRiskScoreBuildUp({ riskData }) {
    return (
      <div data-testid="risk-score-buildup">
        <span>Risk Score: {riskData?.risk_score?.value || "N/A"}</span>
        <span>Administration: {riskData?.administration?.name || "None"}</span>
      </div>
    );
  };
});

jest.mock("../SectorCard", () => {
  return function MockSectorCard({ sectorName, activities, onActivityClick }) {
    return (
      <div data-testid={`sector-${sectorName}`}>
        <h3>{sectorName}</h3>
        {activities.map((act) => (
          <button key={act.id} onClick={() => onActivityClick(act.id)}>
            {act.title}
          </button>
        ))}
      </div>
    );
  };
});

jest.mock("../ActivitySlideIn", () => {
  return function MockActivitySlideIn({ activityId, onClose }) {
    if (!activityId) return null;
    return (
      <div data-testid="activity-drawer">
        <span>Drawer Activity: {activityId}</span>
        <button onClick={onClose}>Close</button>
      </div>
    );
  };
});

const mockActivities = [
  {
    id: 101,
    title: "Drill borehole",
    sector: 1, // WASH
    status: ACTIVITY_STATUS.active,
  },
  {
    id: 102,
    title: "Distribution of Maize Seeds",
    sector: 2, // Agriculture
    status: ACTIVITY_STATUS.active,
  },
];

describe("RiskLevelPage Integration", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders empty state when no Inkhundla is selected", () => {
    useInsights.mockReturnValue({
      selectedInkhundla: null,
      administrationId: null,
      region: null,
      zone: null,
    });

    render(<RiskLevelPage />);
    expect(
      screen.getByText(
        "Please select an Inkhundla from the map or dropdown to view detailed risk insights.",
      ),
    ).toBeInTheDocument();
  });

  it("renders loader initially when Inkhundla is selected", async () => {
    useInsights.mockReturnValue({
      selectedInkhundla: "Nkwene",
      administrationId: 1,
      region: "Shiselweni",
      zone: "Middleveld",
    });

    // Make api calls resolve slowly
    api.mockReturnValue(new Promise(() => {}));

    render(<RiskLevelPage />);
    expect(
      screen.getByText("Loading risk level details..."),
    ).toBeInTheDocument();
  });

  it("fetches active activities and risk score, then renders dashboard successfully", async () => {
    useInsights.mockReturnValue({
      selectedInkhundla: "Nkwene",
      administrationId: 1,
      region: "Shiselweni",
      zone: "Middleveld",
    });

    // Mock API responses
    api.mockImplementation((method, url) => {
      if (url.includes("/risk-levels/")) {
        return Promise.resolve({
          administration: { id: 1, name: "Nkwene" },
          risk_score: { value: 3.5 },
          drought: {
            key: "D3",
            label: "D3 — Extreme drought",
          },
        });
      }
      if (url.includes("/activities")) {
        return Promise.resolve({ data: mockActivities });
      }
      return Promise.resolve({});
    });

    render(<RiskLevelPage />);

    // Loader should go away
    await waitFor(() => {
      expect(
        screen.queryByText("Loading risk level details..."),
      ).not.toBeInTheDocument();
    });

    // Verify Risk Score Build-up section rendered
    expect(screen.getByTestId("risk-score-buildup")).toBeInTheDocument();
    expect(screen.getByText("Risk Score: 3.5")).toBeInTheDocument();
    expect(screen.getByText("Administration: Nkwene")).toBeInTheDocument();

    // Verify Selected Inkhundla Header is rendered
    expect(screen.getByText("Nkwene Inkhundla")).toBeInTheDocument();
    expect(screen.getByText("Shiselweni · Middleveld")).toBeInTheDocument();
    expect(screen.getByText("D3")).toBeInTheDocument();
    expect(screen.getByText("D3 Extreme Drought")).toBeInTheDocument();

    // Verify recommended activities section and sector cards
    expect(screen.getByText("All response activities")).toBeInTheDocument();
    expect(screen.getByTestId("sector-Water & Sanitation")).toBeInTheDocument();
    expect(screen.getByTestId("sector-Food & Agriculture")).toBeInTheDocument();

    // Verify activity buttons are present
    expect(screen.getByText("Drill borehole")).toBeInTheDocument();
    expect(screen.getByText("Distribution of Maize Seeds")).toBeInTheDocument();
  });

  it("opens the slide-in detail drawer when an activity is clicked", async () => {
    useInsights.mockReturnValue({
      selectedInkhundla: "Nkwene",
      administrationId: 1,
      region: "Shiselweni",
      zone: "Middleveld",
    });

    api.mockImplementation((method, url) => {
      if (url.includes("/risk-levels/")) {
        return Promise.resolve({
          administration: { id: 1, name: "Nkwene" },
          risk_score: { value: 3.5 },
          drought: {
            key: "D3",
            label: "D3 — Extreme drought",
          },
        });
      }
      if (url.includes("/activities")) {
        return Promise.resolve({ data: mockActivities });
      }
      return Promise.resolve({});
    });

    render(<RiskLevelPage />);

    await waitFor(() => {
      expect(
        screen.queryByText("Loading risk level details..."),
      ).not.toBeInTheDocument();
    });

    // Drawer should not be present initially
    expect(screen.queryByTestId("activity-drawer")).not.toBeInTheDocument();

    // Click activity button to trigger drawer opening
    fireEvent.click(screen.getByText("Drill borehole"));

    // Verify drawer opened with activity ID
    expect(screen.getByTestId("activity-drawer")).toBeInTheDocument();
    expect(screen.getByText("Drawer Activity: 101")).toBeInTheDocument();

    // Click close button on drawer
    fireEvent.click(screen.getByText("Close"));

    // Drawer should be removed
    expect(screen.queryByTestId("activity-drawer")).not.toBeInTheDocument();
  });

  it("handles non-array activities API error response gracefully without crashing", async () => {
    useInsights.mockReturnValue({
      selectedInkhundla: "Nkwene",
      administrationId: 1,
      region: "Shiselweni",
      zone: "Middleveld",
    });

    // Mock API error response for activities
    api.mockImplementation((method, url) => {
      if (url.includes("/risk-levels/")) {
        return Promise.resolve({
          administration: { id: 1, name: "Nkwene" },
          risk_score: { value: 3.5 },
          drought: {
            key: "D3",
            label: "D3 — Extreme drought",
          },
        });
      }
      if (url.includes("/activities")) {
        // Return 401/403 style error payload instead of array or {data: array}
        return Promise.resolve({
          detail: "Authentication credentials were not provided.",
        });
      }
      return Promise.resolve({});
    });

    render(<RiskLevelPage />);

    // Loader should go away
    await waitFor(() => {
      expect(
        screen.queryByText("Loading risk level details..."),
      ).not.toBeInTheDocument();
    });

    // Confirm dashboard renders successfully despite activities fetch failure
    expect(screen.getByTestId("risk-score-buildup")).toBeInTheDocument();
    expect(screen.getByText("All response activities")).toBeInTheDocument();
  });
});
