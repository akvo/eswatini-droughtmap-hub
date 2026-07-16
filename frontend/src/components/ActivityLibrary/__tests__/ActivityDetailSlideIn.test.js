import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import ActivityDetailSlideIn from "../ActivityDetailSlideIn";
import { api } from "@/lib/api";
import { ACTIVITY_STATUS, USER_ROLES } from "@/static/config";

// Mock the api function
jest.mock("@/lib/api", () => ({
  api: jest.fn(),
  getSourceFileBase64: jest.fn(),
}));

const mockActivity = {
  id: 12,
  code: "ACT-WASH-12",
  title: "Emergency Water Trucking",
  description: "Provide emergency water deliveries.",
  sector: 3,
  sector_label: "Water & Sanitation",
  status: ACTIVITY_STATUS.draft,
  owner: "Ministry of Water",
  coord_with: "NDRMA",
  response_type: 2,
  response_type_label: "Institutional",
  source_doc: "National Response Plan 2026",
  source_file: "uploads/plan.pdf",
  version: "v1.2",
  updated_at: "2026-06-15T10:00:00Z",
  activated_by_name: "John Doe",
  activated_at: "2026-06-16T12:00:00Z",
  notes: "High priority wash activity.",
  triggers: {
    dclass: { class: 3, months: 2 },
    vuln: { op: 1, value: 3 },
    exp: [{ indicator: "water", op: 1, value: 5000 }],
    other: "Dry forecast",
  },
};

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

describe("ActivityDetailSlideIn Component", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("fetches and renders activity details correctly", async () => {
    api.mockResolvedValueOnce(mockActivity); // For detail fetch
    api.mockResolvedValueOnce({ matched: 12, total: 59 }); // For trigger preview

    render(
      <ActivityDetailSlideIn
        activityId={12}
        onClose={jest.fn()}
        onEdit={jest.fn()}
        onRefresh={jest.fn()}
      />,
    );

    // Wait for the detail fetch to complete
    await waitFor(() => {
      expect(screen.getByText("Emergency Water Trucking")).toBeInTheDocument();
    });

    expect(screen.getByText("ACT-WASH-12")).toBeInTheDocument();
    expect(screen.getByText("Water & Sanitation")).toBeInTheDocument();
    expect(screen.getByText("Ministry of Water")).toBeInTheDocument();
    expect(screen.getByText("NDRMA")).toBeInTheDocument();
    expect(screen.getByText("Institutional")).toBeInTheDocument();
    expect(screen.getByText("National Response Plan 2026")).toBeInTheDocument();
    expect(screen.getByText("Download source file")).toBeInTheDocument();
    expect(screen.getByText("v1.2")).toBeInTheDocument();
    expect(screen.getByText("15/06/2026")).toBeInTheDocument(); // updated_at date format
    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("16/06/2026")).toBeInTheDocument(); // activated_at date format
    expect(
      screen.getByText("High priority wash activity."),
    ).toBeInTheDocument();
  });

  it("calls onClose when escape key is pressed", async () => {
    api.mockResolvedValueOnce(mockActivity);
    api.mockResolvedValueOnce({ matched: 12, total: 59 });

    const handleClose = jest.fn();
    render(
      <ActivityDetailSlideIn
        activityId={12}
        onClose={handleClose}
        onEdit={jest.fn()}
        onRefresh={jest.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Emergency Water Trucking")).toBeInTheDocument();
    });

    fireEvent.keyDown(window, { key: "Escape", code: "Escape" });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
