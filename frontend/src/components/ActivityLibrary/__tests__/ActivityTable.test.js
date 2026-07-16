import React from "react";
import { render, screen } from "@testing-library/react";
import ActivityTable from "../ActivityTable";
import { ACTIVITY_STATUS } from "@/static/config";

const mockActivities = [
  {
    id: 1,
    code: "ACT-WASH-1",
    title: "Borehole reinforcement",
    sector: 3,
    sector_label: "Water & Sanitation",
    status: ACTIVITY_STATUS.active,
    owner: "Eswatini Red Cross",
    version: "v1.0",
    updated_at: "2026-05-26T06:12:00Z",
  },
];

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

describe("ActivityTable Component", () => {
  it("renders correctly with rows and column values", () => {
    render(<ActivityTable activities={mockActivities} total={1} page={1} />);

    expect(screen.getByText("Borehole reinforcement")).toBeInTheDocument();
    expect(screen.getByText("ACT-WASH-1")).toBeInTheDocument();
    expect(screen.getByText("Water & Sanitation")).toBeInTheDocument();
    expect(screen.getByText("Eswatini Red Cross")).toBeInTheDocument();
    expect(screen.getByText("26/05/2026")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("calls onRowClick when a row is clicked", () => {
    const handleRowClick = jest.fn();
    render(
      <ActivityTable
        activities={mockActivities}
        total={1}
        page={1}
        onRowClick={handleRowClick}
      />,
    );

    const cell = screen.getByText("Borehole reinforcement");
    cell.closest("tr").click();

    expect(handleRowClick).toHaveBeenCalledTimes(1);
    expect(handleRowClick).toHaveBeenCalledWith(mockActivities[0]);
  });
});
