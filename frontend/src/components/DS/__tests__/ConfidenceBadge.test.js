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

  it("shows Pending, not a dash, when the station is simply too new", () => {
    // Stations came online late May 2026: a June review cannot have a
    // 3-month rainfall window yet. That is "not yet", not "broken".
    render(<ConfidenceBadge band={null} reason="station_history_too_short" />);
    expect(screen.getByText("Pending")).toHaveAttribute(
      "title",
      expect.stringMatching(/started reporting after/),
    );
    expect(screen.queryByText("—")).not.toBeInTheDocument();
  });

  it("does not invent a tooltip for an unknown reason key", () => {
    render(<ConfidenceBadge band={null} reason="something_new" />);
    expect(screen.getByText("—")).not.toHaveAttribute("title");
  });
});
