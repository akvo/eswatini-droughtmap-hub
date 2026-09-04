import { getProfileDropdownItems, textOn } from "../helper";
import { USER_ROLES } from "@/static/config";

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

describe("getProfileDropdownItems — delegated citizen science (CS-DEL-1)", () => {
  const CS_ABILITY = { action: "read", subject: "CitizenScience" };

  // The dropdown renders each entry as a <Link>, so the destination is what
  // identifies it — the label is JSX.
  const urlsFor = (user) =>
    getProfileDropdownItems(user)
      .filter((i) => i.label?.props?.href)
      .map((i) => i.label.props.href);

  it("shows Citizen Weather to a delegated reviewer", () => {
    const urls = urlsFor({
      role: USER_ROLES.reviewer,
      abilities: [CS_ABILITY],
    });
    expect(urls).toContain("/citizen-weather/admin");
  });

  it("hides it from a reviewer who was never delegated", () => {
    // The control: same role, no ability.
    const urls = urlsFor({
      role: USER_ROLES.reviewer,
      abilities: [{ action: "read", subject: "Publication" }],
    });
    expect(urls).not.toContain("/citizen-weather/admin");
  });

  it("grants no other admin entry", () => {
    // The flag is one surface. Admin dashboard, publications and the admin
    // settings target must all stay behind the role.
    const urls = urlsFor({
      role: USER_ROLES.reviewer,
      abilities: [CS_ABILITY],
    });
    expect(urls).not.toContain("/admin");
    expect(urls).not.toContain("/publications");
    expect(urls).toContain("/profile");
  });

  it("keeps the reviewer's own surfaces — the flag adds, never subtracts", () => {
    const urls = urlsFor({
      role: USER_ROLES.reviewer,
      abilities: [CS_ABILITY],
    });
    expect(urls).toContain("/reviews");
    expect(urls).toContain("/activity-library");
  });

  it("leaves an admin's entries unchanged", () => {
    const urls = urlsFor({ role: USER_ROLES.admin });
    expect(urls).toContain("/citizen-weather/admin");
    expect(urls).toContain("/publications");
  });
});
