import { render } from "@testing-library/react";
import MethodologyPage from "../page";
import { sectionsConfig } from "@/static/methodology";
import { DROUGHT_CATEGORY_CODE, DROUGHT_CATEGORY_VALUE } from "@/static/config";

describe("MethodologyPage", () => {
  it("renders every reference table's heading and rows", () => {
    const { getByText, getAllByRole } = render(<MethodologyPage />);

    sectionsConfig.forEach((section) => {
      expect(getByText(section.title)).toBeInTheDocument();
    });

    // +1 header row per table.
    const expectedRows = sectionsConfig.reduce(
      (total, section) => total + section.rows.length + 1,
      0,
    );
    expect(getAllByRole("row")).toHaveLength(expectedRows);
  });

  it("renders D-class cells as drought chips, not raw category values", () => {
    const { getByText } = render(<MethodologyPage />);

    // The hazard table stores DROUGHT_CATEGORY_VALUE codes; the `drought`
    // column type must turn them into chips. Without it the cells would print
    // the raw values ("0", "5", …) and these lookups would find nothing.
    expect(
      getByText(DROUGHT_CATEGORY_CODE[DROUGHT_CATEGORY_VALUE.d4]),
    ).toBeInTheDocument();
    expect(
      getByText(DROUGHT_CATEGORY_CODE[DROUGHT_CATEGORY_VALUE.normal]),
    ).toBeInTheDocument();
  });
});
