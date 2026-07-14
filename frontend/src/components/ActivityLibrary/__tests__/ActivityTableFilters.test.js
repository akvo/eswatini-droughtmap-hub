import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ActivityTableFilters from "../ActivityTableFilters";

describe("ActivityTableFilters Component", () => {
  const onStatusChange = jest.fn();
  const onSectorChange = jest.fn();
  const onSearchChange = jest.fn();
  const onExport = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders filter elements and handles events", async () => {
    render(
      <ActivityTableFilters
        statusFilter="all"
        sectorFilter="all"
        searchQuery=""
        onStatusChange={onStatusChange}
        onSectorChange={onSectorChange}
        onSearchChange={onSearchChange}
        onExport={onExport}
      />,
    );

    // Assert title & static text
    expect(screen.getByText("Operation procedures")).toBeInTheDocument();

    // Verify search input type & debounced fire
    const searchInput = screen.getByPlaceholderText(
      "Search by title or code...",
    );
    fireEvent.change(searchInput, { target: { value: "Borehole" } });

    await waitFor(() => {
      expect(onSearchChange).toHaveBeenCalledWith("Borehole");
    });

    // Verify CSV Export triggers
    const exportBtn = screen.getByText("Export CSV");
    fireEvent.click(exportBtn);
    expect(onExport).toHaveBeenCalled();
  });
});
