import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import ResponseAndNotify from "../sections/ResponseAndNotify";

// Exactly what /activities?status=active returns, including the
// `description` that was added to ActivityListSerializer for this section.
const ACTIVITIES = [
  {
    id: 1,
    code: "ACT-WASH-1",
    title: "Emergency water tankering",
    description: "Dispatch tankers to affected Tinkhundla",
    sector: 3,
    sector_label: "Water & Sanitation",
    owner: "Department of Water Affairs",
    trigger_summary: "D2+ for 3 mo · IPC >= Phase 2 · population >= 2000.0",
  },
];

const renderActivities = (activities = ACTIVITIES) =>
  render(
    <ResponseAndNotify
      showActivities
      showNotify={false}
      activities={activities}
    />,
  );

describe("Response activities", () => {
  it("shows the activity code alongside the title", () => {
    renderActivities();
    expect(screen.getByText("Emergency water tankering")).toBeInTheDocument();
    expect(screen.getByText("ACT-WASH-1")).toBeInTheDocument();
  });

  it("collapses the detail until the toggle is pressed", () => {
    renderActivities();

    const toggle = screen.getByRole("button", { expanded: false });
    const detail = screen.getByTestId("activity-detail");

    expect(detail).toHaveTextContent("Dispatch tankers to affected Tinkhundla");
    expect(detail).toHaveTextContent(
      "D2+ for 3 mo · IPC >= Phase 2 · population >= 2000.0",
    );

    // Hidden on screen but never removed: the print variant is what keeps
    // the description and triggers on paper when the reader left the card
    // collapsed.
    expect(detail).toHaveClass("hidden", "print:flex");

    fireEvent.click(toggle);
    expect(screen.getByRole("button", { expanded: true })).toBe(toggle);
    expect(detail).toHaveClass("flex");
    expect(detail).not.toHaveClass("hidden");
  });

  it("expands on description alone when the rest is missing", () => {
    renderActivities([
      {
        id: 3,
        code: "ACT-Y-1",
        title: "Description only",
        description: "Stand up coordination cells",
      },
    ]);
    expect(screen.getByRole("button", { expanded: false })).toBeInTheDocument();
    expect(screen.getByTestId("activity-detail")).toHaveTextContent(
      "Stand up coordination cells",
    );
  });

  it("omits the toggle when the payload carries nothing to expand", () => {
    renderActivities([{ id: 2, code: "ACT-X-1", title: "Bare activity" }]);
    expect(screen.getByText("Bare activity")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("keeps the empty state when no activities are triggered", () => {
    renderActivities([]);
    expect(
      screen.getByText(/No active activities are triggered/i),
    ).toBeInTheDocument();
  });
});
