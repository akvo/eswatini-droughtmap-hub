import React from "react";
import { render, screen } from "@testing-library/react";
import ActivityMetricCards from "../ActivityMetricCards";

describe("ActivityMetricCards Component", () => {
  it("renders metric counts correctly", () => {
    render(<ActivityMetricCards active={12} draft={3} archived={5} />);

    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();

    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();

    expect(screen.getByText("Archived")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });
});
