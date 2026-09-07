import { fireEvent, render, screen } from "@testing-library/react";
import ConfidenceCoverageAlert from "../ConfidenceCoverageAlert";

const NONE = {
  scored: 0,
  total: 59,
  unscored: [
    { key: "incomplete_station_record", value: 41 },
    { key: "no_station_in_region", value: 18 },
  ],
};

const PARTIAL = {
  scored: 40,
  total: 59,
  unscored: [{ key: "no_station_in_region", value: 19 }],
};

describe("ConfidenceCoverageAlert", () => {
  it("renders nothing when every Inkhundla is scored", () => {
    const { container } = render(
      <ConfidenceCoverageAlert
        coverage={{ scored: 59, total: 59, unscored: [] }}
        yearMonth="2026-08"
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when coverage is missing entirely", () => {
    const { container } = render(<ConfidenceCoverageAlert />);
    expect(container).toBeEmptyDOMElement();
  });

  it("warns and explains the missing shortcut when nothing is scored", () => {
    render(<ConfidenceCoverageAlert coverage={NONE} yearMonth="2026-07" />);
    expect(
      screen.getByText("No confidence scores for July 2026."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/bulk-accept shortcut is unavailable/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /the station did not report enough of the last 3 months/i,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/no weather station in this Inkhundla's region/i),
    ).toBeInTheDocument();
  });

  it("uses the quieter register when only some are unscored", () => {
    render(<ConfidenceCoverageAlert coverage={PARTIAL} yearMonth="2026-08" />);
    expect(
      screen.getByText(
        "19 of 59 Tinkhundla have no confidence score for August 2026.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/bulk-accepted as usual/)).toBeInTheDocument();
    expect(
      screen.queryByText(/bulk-accept shortcut is unavailable/),
    ).not.toBeInTheDocument();
  });

  it("collapses the breakdown but keeps the headline", () => {
    render(<ConfidenceCoverageAlert coverage={NONE} yearMonth="2026-07" />);
    const reason = /the station did not report enough of the last 3 months/i;
    expect(screen.getByText(reason)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /hide/i }));
    expect(screen.queryByText(reason)).not.toBeInTheDocument();
    // The standing condition must remain visible when collapsed.
    expect(
      screen.getByText("No confidence scores for July 2026."),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /details/i }));
    expect(screen.getByText(reason)).toBeInTheDocument();
  });

  it("is not dismissible", () => {
    render(<ConfidenceCoverageAlert coverage={NONE} yearMonth="2026-07" />);
    expect(screen.queryByRole("button", { name: /close/i })).toBeNull();
  });

  it("never prints a raw slug for an unrecognised reason", () => {
    render(
      <ConfidenceCoverageAlert
        coverage={{
          scored: 0,
          total: 3,
          unscored: [{ key: "some_new_backend_reason", value: 3 }],
        }}
        yearMonth="2026-07"
      />,
    );
    expect(screen.queryByText(/some_new_backend_reason/)).toBeNull();
    expect(screen.getByText(/reason not recorded/)).toBeInTheDocument();
    expect(screen.getByText("3 Tinkhundla")).toBeInTheDocument();
  });
});
