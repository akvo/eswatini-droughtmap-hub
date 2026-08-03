import { render, screen } from "@testing-library/react";
import ResponseActivities from "../ResponseActivities";
import { responseActivitiesData } from "@/static/mocks/national-overview/response-activities";

describe("ResponseActivities", () => {
  it("renders a sector icon for every sector key", () => {
    const { container } = render(<ResponseActivities />);
    // guards the mock-key -> SECTORS id map: a bad key renders no <img>
    expect(container.querySelectorAll("img")).toHaveLength(
      responseActivitiesData.sectors.length,
    );
  });

  it("links to the priority areas page", () => {
    render(<ResponseActivities />);
    expect(
      screen.getByRole("link", {
        name: /Open Response Activities page per Inkhundla/i,
      }),
    ).toHaveAttribute("href", responseActivitiesData.priorityAreasHref);
  });
});
