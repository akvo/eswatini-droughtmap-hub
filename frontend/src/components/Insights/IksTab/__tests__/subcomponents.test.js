import { render, screen, fireEvent } from "@testing-library/react";
import KpiMetricCard from "../KpiMetricCard";
import MonthlyStatusGrid from "../MonthlyStatusGrid";
import IndicatorRow, { formatMonthLabel } from "../IndicatorRow";
import PredictorAccordion from "../PredictorAccordion";

// Mock matchMedia for Ant Design responsiveness in JSDOM tests
beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: jest.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
});

describe("IksTab Subcomponents", () => {
  describe("KpiMetricCard", () => {
    it("renders title, value, and subtitle correctly", () => {
      render(
        <KpiMetricCard
          title="Reporting Consistency"
          value="95%"
          subtitle="Updated monthly"
        />,
      );
      expect(screen.getByText("Reporting Consistency")).toBeInTheDocument();
      expect(screen.getByText("95%")).toBeInTheDocument();
      expect(screen.getByText("Updated monthly")).toBeInTheDocument();
    });
  });

  describe("MonthlyStatusGrid", () => {
    it("renders title, subtitle, months and grid states", () => {
      const mockStatesMap = jest.fn((idx) => (idx === 0 ? "G" : "B"));
      const mockLegend = [
        { label: "Generally Green", color: "bg-[#12b76a]" },
        { label: "Brown", color: "bg-[#b10d0b]" },
      ];

      render(
        <MonthlyStatusGrid
          title="Vegetation Greenness"
          subtitle="One answer per month"
          statesMap={mockStatesMap}
          legend={mockLegend}
          weeks={["Jan", "Feb"]}
        />,
      );

      expect(screen.getByText("Vegetation Greenness")).toBeInTheDocument();
      expect(screen.getByText("One answer per month")).toBeInTheDocument();
      expect(screen.getByText("Jan")).toBeInTheDocument();
      expect(screen.getByText("Feb")).toBeInTheDocument();
      expect(screen.getByText("G")).toBeInTheDocument();
      expect(screen.getByText("B")).toBeInTheDocument();
      expect(screen.getByText("Generally Green")).toBeInTheDocument();
      expect(screen.getByText("Brown")).toBeInTheDocument();
    });

    it("greys out a month with no submission instead of using the brand blue", () => {
      render(
        <MonthlyStatusGrid
          title="Soil moisture"
          subtitle="One answer per month"
          statesMap={() => "-"}
          legend={[{ label: "Dry", color: "bg-[#b10d0b]" }]}
          weeks={["Jan"]}
        />,
      );

      // #3e5eb9 is --primary-color: an unreported month must not read as the
      // most prominent thing on the row.
      const cell = screen.getByText("-").parentElement;
      expect(cell).toHaveClass("bg-[#9ca3af]");
      expect(cell).not.toHaveClass("bg-[#3e5eb9]");
    });
  });

  describe("IndicatorRow", () => {
    it("formats month strings correctly", () => {
      expect(formatMonthLabel("2026-01")).toBe("Jan");
      expect(formatMonthLabel("2026-12")).toBe("Dec");
      expect(formatMonthLabel("invalid")).toBe("invalid");
      expect(formatMonthLabel(null)).toBe("");
    });

    it("renders row title and month strips", () => {
      render(
        <IndicatorRow
          name="Blue swallows appearance"
          isDroughtLeaning={false}
          months={["2026-01", "2026-02"]}
          checkedMonths={[true, false]}
        />,
      );
      expect(screen.getByText("Blue swallows appearance")).toBeInTheDocument();
    });
  });

  describe("PredictorAccordion", () => {
    it("renders accordion header, collapsible panels, and indicator rows", () => {
      const mockItems = [
        {
          key: "birds",
          header: "Birds",
          indicators: [
            { dbKey: "bs", name: "Blue swallows", isDroughtLeaning: false },
          ],
        },
      ];

      render(
        <PredictorAccordion
          title="Section B"
          subtitle="Rainfall predictors"
          items={mockItems}
          months={["2026-01"]}
          indicatorsData={{ bs: [true] }}
        />,
      );

      expect(screen.getByText("Section B")).toBeInTheDocument();
      expect(screen.getByText("Rainfall predictors")).toBeInTheDocument();
      expect(screen.getByText("Birds")).toBeInTheDocument();

      // Click the header to expand and render the indicators
      fireEvent.click(screen.getByText("Birds"));
      expect(screen.getByText("Blue swallows")).toBeInTheDocument();
    });
  });
});
