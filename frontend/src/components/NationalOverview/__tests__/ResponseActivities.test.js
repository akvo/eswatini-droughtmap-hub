import { render, screen } from "@testing-library/react";
import ResponseActivities from "../ResponseActivities";
import { responseActivitiesData } from "@/static/mocks/national-overview/response-activities";

describe("ResponseActivities", () => {
  it("renders a sector icon for every sector key", () => {
    const { container } = render(
      <ResponseActivities responseActivities={responseActivitiesData} />,
    );
    // guards the mock-key -> SECTORS id map: a bad key renders no <img>
    expect(container.querySelectorAll("img")).toHaveLength(
      responseActivitiesData.sectors.length,
    );
  });

  it("links to the priority areas page", () => {
    render(<ResponseActivities responseActivities={responseActivitiesData} />);
    expect(
      screen.getByRole("link", {
        name: /Open Response Activities page per Inkhundla/i,
      }),
    ).toHaveAttribute("href", responseActivitiesData.priorityAreasHref);
  });

  it("shows the skeleton until data arrives", () => {
    const { container } = render(<ResponseActivities />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(container.querySelector(".ant-skeleton")).toBeTruthy();
  });
});
