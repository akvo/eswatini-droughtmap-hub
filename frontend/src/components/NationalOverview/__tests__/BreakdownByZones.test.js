import { render, screen } from "@testing-library/react";
import BreakdownByZones from "../BreakdownByZones";

const mockPrint = { printMode: false };
jest.mock("@/context/PrintContextProvider", () => ({
  usePrintContext: () => mockPrint,
}));

// akvo-charts renders through ECharts, which JSDOM has no canvas for.
jest.mock("akvo-charts", () => ({
  Doughnut: () => <div data-testid="doughnut" />,
}));

const zoneData = (labels) => ({
  zones: { data: labels.map((label, id) => ({ id, label, value: 0 })) },
  trends: { data: [] },
  breakdowns: { data: [] },
});

const climaticData = zoneData(["Highveld", "Lubombo Range"]);
const regionsData = zoneData(["Hhohho", "Manzini"]);

describe("BreakdownByZones — print expansion (INS-PDF-1 D-9)", () => {
  afterEach(() => {
    mockPrint.printMode = false;
  });

  it("shows only the selected grouping on screen", () => {
    mockPrint.printMode = false;
    render(
      <BreakdownByZones
        regionsData={regionsData}
        climaticData={climaticData}
      />,
    );

    expect(screen.getByText("Highveld")).toBeInTheDocument();
    // Regions is the unselected tab, so its zones must not be rendered.
    expect(screen.queryByText("Hhohho")).not.toBeInTheDocument();
  });

  it("also renders the other grouping in print mode", () => {
    mockPrint.printMode = true;
    render(
      <BreakdownByZones
        regionsData={regionsData}
        climaticData={climaticData}
      />,
    );

    // Both groupings present, so the PDF carries both tabs.
    expect(screen.getByText("Highveld")).toBeInTheDocument();
    expect(screen.getByText("Hhohho")).toBeInTheDocument();
    expect(
      screen.getByText(/Breakdown by zones — Regions/),
    ).toBeInTheDocument();
  });
});
