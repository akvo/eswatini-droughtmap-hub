import { render, screen } from "@testing-library/react";
import ResponseActivities from "../ResponseActivities";

// Shape mirrors GET /api/v1/insights/response-activities. Kept inline rather
// than in a shared mock file: the endpoint is live, so this is a test fixture,
// not a contract standing in for a missing API.
const responseActivitiesData = {
  lastUpdated: "18 May 2026",
  summary: "7 public response activities currently active across Eswatini.",
  sectors: [
    {
      key: "water",
      label: "Water and Sanitation",
      activities: 2,
      tinkhundla: 15,
      description: "...",
    },
    {
      key: "agriculture",
      label: "Agriculture and Food security",
      activities: 3,
      tinkhundla: 18,
      description: "...",
    },
    {
      key: "environment",
      label: "Environment and energy",
      activities: 2,
      tinkhundla: 5,
      description: "...",
    },
    {
      key: "health",
      label: "Health and nutrition",
      activities: 2,
      tinkhundla: 5,
      description: "...",
    },
  ],
  priorityAreasHref: "/detailed-insights/risk-level",
};

describe("ResponseActivities", () => {
  it("renders a sector icon for every sector key", () => {
    const { container } = render(
      <ResponseActivities responseActivities={responseActivitiesData} />,
    );
    // guards the API-key -> SECTORS id map: a bad key renders no <img>
    expect(container.querySelectorAll("img")).toHaveLength(
      responseActivitiesData.sectors.length,
    );
  });

  it("links to the brief builder page", () => {
    render(<ResponseActivities responseActivities={responseActivitiesData} />);
    expect(
      screen.getByRole("link", {
        name: /Open Response Activities page per Inkhundla/i,
      }),
    ).toHaveAttribute("href", "/brief-builder");
  });

  it("shows the skeleton until data arrives", () => {
    const { container } = render(<ResponseActivities />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(container.querySelector(".ant-skeleton")).toBeTruthy();
  });
});
