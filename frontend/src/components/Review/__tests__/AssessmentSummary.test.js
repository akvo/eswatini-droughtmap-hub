import { render, screen } from "@testing-library/react";
import AssessmentSummary from "../AssessmentSummary";

const card = (value) => ({
  key: "fully_reviewed",
  label: "Fully reviewed",
  value,
  note: "of queue | ready to validate",
  delta: { value: 3, direction: "up" },
});

const summary = (value) => ({ status_breakdown: [card(value)] });
const emptyNote = () => screen.queryByText(/No data available/);

describe("AssessmentSummary breakdown cards", () => {
  it("swaps the note and drops the delta at zero", () => {
    render(<AssessmentSummary summary={summary(0)} />);
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(emptyNote()).toBeInTheDocument();
    expect(screen.queryByText(/of queue/)).not.toBeInTheDocument();
    expect(screen.queryByText(/↑/)).not.toBeInTheDocument();
  });

  it("keeps the note and the delta once the card counts something", () => {
    render(<AssessmentSummary summary={summary(4)} />);
    expect(emptyNote()).not.toBeInTheDocument();
    expect(screen.getByText(/of queue/)).toBeInTheDocument();
    expect(screen.getByText(/↑/)).toBeInTheDocument();
  });
});
