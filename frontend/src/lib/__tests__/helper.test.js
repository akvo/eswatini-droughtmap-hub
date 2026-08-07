import { textOn } from "../helper";

describe("textOn relative luminance text color contrast utility", () => {
  it("should return dark gray text (#1f2937) for light background colors", () => {
    // Normal / Light Green
    expect(textOn("#12b76a")).toBe("#ffffff");
    // D0 / Yellow
    expect(textOn("#ffff00")).toBe("#333333");
    // D1 / Light Orange/Yellow
    expect(textOn("#fbd47f")).toBe("#333333");
    // None / White
    expect(textOn("#ffffff")).toBe("#333333");
  });

  it("should return white text (#ffffff) for dark background colors", () => {
    // D3 / Red
    expect(textOn("#e60000")).toBe("#ffffff");
    // D4 / Dark Red
    expect(textOn("#730000")).toBe("#ffffff");
  });

  it("should default to white text (#ffffff) on missing or invalid inputs", () => {
    expect(textOn(null)).toBe("#ffffff");
    expect(textOn(undefined)).toBe("#ffffff");
    expect(textOn("")).toBe("#ffffff");
    expect(textOn("invalid-color")).toBe("#ffffff");
  });
});
