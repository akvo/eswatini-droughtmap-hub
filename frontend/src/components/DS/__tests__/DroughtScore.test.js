import { render, screen } from "@testing-library/react";
import DroughtScore from "../DroughtScore";
import { DROUGHT_CATEGORY_VALUE } from "@/static/config";

/** The chip renders its code; this reads back the ink actually applied. */
const inkFor = (level) => {
  const { unmount } = render(<DroughtScore level={level} />);
  const chip = screen.getByTitle(/./);
  const { color } = chip.style;
  unmount();
  return color;
};

describe("DroughtScore ink", () => {
  it("puts dark text on the light steps", () => {
    // White on D0 (#ffff00) is 1.07:1 contrast — the chip was unreadable.
    expect(inkFor(DROUGHT_CATEGORY_VALUE.d0)).toBe("rgb(51, 51, 51)");
    expect(inkFor(DROUGHT_CATEGORY_VALUE.d1)).toBe("rgb(51, 51, 51)");
    expect(inkFor(DROUGHT_CATEGORY_VALUE.d2)).toBe("rgb(51, 51, 51)");
  });

  it("keeps white text on the dark steps", () => {
    expect(inkFor(DROUGHT_CATEGORY_VALUE.normal)).toBe("rgb(255, 255, 255)");
    expect(inkFor(DROUGHT_CATEGORY_VALUE.d3)).toBe("rgb(255, 255, 255)");
    expect(inkFor(DROUGHT_CATEGORY_VALUE.d4)).toBe("rgb(255, 255, 255)");
  });

  it("keeps the white 'No data' swatch readable", () => {
    expect(inkFor(DROUGHT_CATEGORY_VALUE.none)).toBe("rgb(51, 51, 51)");
  });
});
