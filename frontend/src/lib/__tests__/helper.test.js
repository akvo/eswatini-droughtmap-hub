import { textOn } from "../helper";

describe("textOn relative luminance text color contrast utility", () => {
  it("should return dark gray text (#1f2937) for light background colors", () => {
    // Normal / Light Green
    expect(textOn("#b9f8cf")).toBe("#1f2937");
    // D0 / Yellow
    expect(textOn("#ffff00")).toBe("#1f2937");
    // D1 / Light Orange/Yellow
    expect(textOn("#fbd47f")).toBe("#1f2937");
    // None / White
    expect(textOn("#ffffff")).toBe("#1f2937");
    // Short hex white
    expect(textOn("#fff")).toBe("#1f2937");
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
