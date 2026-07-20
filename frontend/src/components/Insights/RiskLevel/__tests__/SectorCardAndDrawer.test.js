import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SectorCard from "../SectorCard";
import ActivitySlideIn from "../ActivitySlideIn";
import { api } from "@/lib/api";

// Mock the API client
jest.mock("@/lib/api", () => ({
  api: jest.fn(),
}));

describe("SectorCard Component", () => {
  const mockActivities = [
    {
      id: 1,
      code: "ACT-WASH-1",
      title: "Emergency water trucking",
      owner_label: "NDMA / Ministry of Water",
    },
    {
      id: 2,
      code: "ACT-WASH-3",
      title: "Borehole rehabilitation",
      owner_label: "NDMA",
    },
  ];

  it("renders sector name and description correctly", () => {
    render(
      <SectorCard
        sectorKey={3}
        sectorName="Water & Sanitation"
        description="Water descriptions here."
        activities={mockActivities}
      />,
    );

    expect(screen.getByText("Water & Sanitation")).toBeInTheDocument();
    expect(screen.getByText("Water descriptions here.")).toBeInTheDocument();
  });

  it("renders correct number of activity cards with labels", () => {
    render(
      <SectorCard
        sectorKey={3}
        sectorName="Water & Sanitation"
        description="Water descriptions here."
        activities={mockActivities}
      />,
    );

    expect(screen.getByText("ACT-WASH-1")).toBeInTheDocument();
    expect(screen.getByText("Emergency water trucking")).toBeInTheDocument();
    expect(screen.getByText("ACT-WASH-3")).toBeInTheDocument();
    expect(screen.getByText("Borehole rehabilitation")).toBeInTheDocument();
  });

  it("triggers onActivityClick when a card is clicked", () => {
    const handleActivityClick = jest.fn();
    render(
      <SectorCard
        sectorKey={3}
        sectorName="Water & Sanitation"
        activities={mockActivities}
        onActivityClick={handleActivityClick}
      />,
    );

    fireEvent.click(screen.getByText("Emergency water trucking"));
    expect(handleActivityClick).toHaveBeenCalledWith(1);
  });

  it("renders empty state correctly when there are no activities", () => {
    render(
      <SectorCard
        sectorKey={3}
        sectorName="Water & Sanitation"
        activities={[]}
      />,
    );

    expect(
      screen.getByText(
        "No active activities currently defined in this sector.",
      ),
    ).toBeInTheDocument();
  });
});

describe("ActivitySlideIn Component", () => {
  const mockActivityDetail = {
    id: 1,
    code: "ACT-WASH-1",
    title: "Emergency water trucking",
    description: "Provide clean drinking water via trucks.",
    sector: 3,
    sector_label: "Water & Sanitation",
    owner_label: "NDMA / Ministry of Water",
    triggers: {
      dclass: 2,
      operator: "gte",
      rules: [{ field: "vWater", operator: "gte", value: 0.75 }],
    },
  };

  beforeEach(() => {
    api.mockClear();
  });

  it("fetches detail and renders details when activityId is set", async () => {
    api.mockResolvedValueOnce(mockActivityDetail);
    const handleClose = jest.fn();

    render(<ActivitySlideIn activityId={1} onClose={handleClose} />);

    // Loader is visible initially
    expect(screen.getByText("Loading activity details...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Emergency water trucking")).toBeInTheDocument();
    });

    expect(screen.getByText("ACT-WASH-1")).toBeInTheDocument();
    expect(
      screen.getByText("Provide clean drinking water via trucks."),
    ).toBeInTheDocument();
    expect(screen.getByText("Response activity details")).toBeInTheDocument();
  });

  it("triggers onClose when close button is clicked", async () => {
    api.mockResolvedValueOnce(mockActivityDetail);
    const handleClose = jest.fn();

    render(<ActivitySlideIn activityId={1} onClose={handleClose} />);

    await waitFor(() => {
      expect(screen.getByText("Emergency water trucking")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("×"));
    expect(handleClose).toHaveBeenCalled();
  });
});
