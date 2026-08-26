import { render, screen } from "@testing-library/react";
import ConfidenceBadge from "../ConfidenceBadge";

describe("ConfidenceBadge", () => {
  it("labels a banded score", () => {
    render(<ConfidenceBadge band="high" />);
    expect(screen.getByText("High")).toBeInTheDocument();
  });

  it("renders a dash when the score is 0 (no band)", () => {
    render(<ConfidenceBadge band={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("explains WHY a 0 could not be scored", () => {
    // A reviewer must be able to tell "we could not compute this" from
    // "we computed it and the sources disagree".
    render(<ConfidenceBadge band={null} reason="no_station_in_region" />);
    expect(screen.getByText("—")).toHaveAttribute(
      "title",
      "No weather station in this Inkhundla's region",
    );
  });

  it("does not invent a tooltip for an unknown reason key", () => {
    render(<ConfidenceBadge band={null} reason="something_new" />);
    expect(screen.getByText("—")).not.toHaveAttribute("title");
  });
});
