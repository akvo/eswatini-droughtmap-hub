import { render, screen } from "@testing-library/react";
import ReviewerMap from "../ReviewerMap";

jest.mock("../CDIMap", () => {
  const CDIMap = () => <div data-testid="cdi-map" />;
  return { __esModule: true, default: CDIMap };
});

jest.mock("@/context/AppContextProvider", () => ({
  useAppContext: () => ({ selectedAdms: [], activeAdm: null }),
}));

const row = (band) => ({ administration_id: 1, confidence: { band } });
const emptyState = () => screen.queryByText("No confidence score data yet");

describe("ReviewerMap confidence empty state", () => {
  it("replaces the map when no Inkhundla has a confidence band", () => {
    render(<ReviewerMap data={[row(null), row(null)]} />);
    expect(emptyState()).toBeInTheDocument();
    expect(screen.queryByTestId("cdi-map")).not.toBeInTheDocument();
    expect(screen.queryByText("No data")).not.toBeInTheDocument();
  });

  it("draws the map as soon as one band is scored", () => {
    render(<ReviewerMap data={[row(null), row("high")]} />);
    expect(emptyState()).not.toBeInTheDocument();
    expect(screen.getByTestId("cdi-map")).toBeInTheDocument();
  });

  it("never empties the progress layer, which does not use bands", () => {
    render(<ReviewerMap data={[row(null)]} mode="progress" />);
    expect(emptyState()).not.toBeInTheDocument();
    expect(screen.getByTestId("cdi-map")).toBeInTheDocument();
  });
});
