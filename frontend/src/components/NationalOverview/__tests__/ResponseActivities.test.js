import { render, screen } from "@testing-library/react";
import ResponseActivities from "../ResponseActivities";

// Shape mirrors GET /api/v1/insights/response-activities. Kept inline rather
// than in a shared mock file: the endpoint is live, so this is a test fixture,
// not a contract standing in for a missing API.
const responseActivitiesData = {
  lastUpdated: "18 May 2026",
  summary: "8 public response activities currently active across Eswatini.",
  // `id` is the ActivitySector id and is what resolves the icon. Social
  // Protection (7) has no icon asset, so it exercises the inline fallback —
  // the case that proves a new sector cannot render iconless.
  sectors: [
    {
      id: 3,
      key: "wash",
      label: "Water & Sanitation",
      activities: 2,
      tinkhundla: 27,
      description: "...",
    },
    {
      id: 1,
      key: "food",
      label: "Food & Agriculture",
      activities: 3,
      tinkhundla: 31,
      description: "...",
    },
    {
      id: 7,
      key: "social",
      label: "Social Protection",
      activities: 2,
      tinkhundla: 12,
      description: "...",
    },
    {
      id: 8,
      key: "trans",
      label: "Transport & Logistics",
      activities: 1,
      tinkhundla: 14,
      description: "...",
    },
  ],
  priorityAreasHref: "/detailed-insights/risk-level",
};

describe("ResponseActivities", () => {
  it("renders a card and an icon for every sector the API returns", () => {
    const { container } = render(
      <ResponseActivities responseActivities={responseActivitiesData} />,
    );
    // Three of the four ids have an icon asset; Social Protection (7) has
    // none and falls back to the inline shield, so every sector is still
    // represented even though only three are <img>.
    expect(container.querySelectorAll("img")).toHaveLength(3);
    expect(container.querySelectorAll("svg").length).toBeGreaterThanOrEqual(1);

    responseActivitiesData.sectors.forEach((sector) => {
      expect(screen.getByText(sector.label)).toBeInTheDocument();
    });
  });

  it("renders however many sectors the API returns, not a fixed four", () => {
    const { container } = render(
      <ResponseActivities
        responseActivities={{
          ...responseActivitiesData,
          sectors: responseActivitiesData.sectors.slice(0, 2),
        }}
      />,
    );
    expect(container.querySelectorAll("img")).toHaveLength(2);
    expect(screen.queryByText("Social Protection")).not.toBeInTheDocument();
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
