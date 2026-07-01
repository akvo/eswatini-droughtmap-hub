import { render, screen, fireEvent } from "@testing-library/react";
import { TabButtons } from "@/components";

const options = [
  { label: "Regions", value: "regions" },
  { label: "Climatic zones", value: "climatic" },
];

describe("TabButtons", () => {
  it("marks the active option and fires onChange on click", () => {
    const onChange = jest.fn();
    render(
      <TabButtons options={options} value="regions" onChange={onChange} />
    );
    expect(screen.getByText("Regions").className).toContain("bg-white");
    expect(screen.getByText("Climatic zones").className).not.toContain(
      "bg-white"
    );
    fireEvent.click(screen.getByText("Climatic zones"));
    expect(onChange).toHaveBeenCalledWith("climatic");
  });
});
