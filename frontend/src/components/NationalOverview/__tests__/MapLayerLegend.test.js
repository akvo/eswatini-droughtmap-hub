import { render, screen } from "@testing-library/react";
import MapLayerLegend from "../MapLayerLegend";

describe("MapLayerLegend", () => {
  it("shows the numeric endpoints of a continuous scale", () => {
    render(
      <MapLayerLegend
        layer={{
          legend: {
            unit: "mm",
            min: 12,
            max: 180,
            continuous: true,
            colors: ["#F7FBFF", "#08306B"],
          },
        }}
      />,
    );
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("180")).toBeInTheDocument();
    expect(screen.getByText("mm")).toBeInTheDocument();
  });

  it("shows one swatch per category", () => {
    render(
      <MapLayerLegend
        layer={{
          legend: {
            categories: [
              { key: "HV", label: "Highveld", color: "#2E7D32" },
              { key: "LR", label: "Lubombo Range", color: "#6D4C41" },
            ],
          },
        }}
      />,
    );
    expect(screen.getByText("Highveld")).toBeInTheDocument();
    expect(screen.getByText("Lubombo Range")).toBeInTheDocument();
  });

  it("builds the D-class legend from frontend config, not the API", () => {
    // The API sends `scheme: "drought"` and no hex at all — the palette has
    // exactly one definition and it is in static/config.
    render(<MapLayerLegend layer={{ legend: { scheme: "drought" } }} />);
    // Short code on screen, full label on hover — as the drought-class
    // legend does, so the strip does not run off the card.
    expect(screen.getByText("D2")).toBeInTheDocument();
    expect(screen.getByText("D2")).toHaveAttribute(
      "title",
      "D2 Severe Drought",
    );
    expect(screen.getByText("Normal")).toBeInTheDocument();
  });

  it("badges a provisional layer", () => {
    render(
      <MapLayerLegend
        layer={{
          legend: { categories: [] },
          meta: { provisional: true, note: "Vintage is not recorded." },
        }}
      />,
    );
    expect(screen.getByTestId("provisional-badge")).toBeInTheDocument();
  });

  it("does not badge a layer once its data is sourced", () => {
    // The self-clearing half of D-9: nothing here special-cases a layer key,
    // so a sourced row simply stops carrying the flag.
    render(
      <MapLayerLegend
        layer={{
          legend: { categories: [{ key: "a", label: "A", color: "#000" }] },
          meta: { source: "WorldPop wpgp 2020", asOf: "2020-01-01" },
        }}
      />,
    );
    expect(screen.queryByTestId("provisional-badge")).not.toBeInTheDocument();
  });

  it("renders nothing when there is no legend and nothing to warn about", () => {
    const { container } = render(<MapLayerLegend layer={{ meta: {} }} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("explains what the layer shows, from the API", () => {
    render(
      <MapLayerLegend
        layer={{
          legend: { continuous: true, min: 0, max: 1, colors: ["#fff"] },
          meta: { description: "Percentile rank, not degrees." },
        }}
      />,
    );
    // The sentence is the accessible name, so it reaches a screen reader
    // without a hover the pointer-less cannot perform.
    expect(
      screen.getByLabelText("Percentile rank, not degrees."),
    ).toBeInTheDocument();
  });

  it("shows no info affordance for a layer the API does not describe", () => {
    render(
      <MapLayerLegend
        layer={{
          legend: { continuous: true, min: 0, max: 1, colors: ["#fff"] },
          meta: {},
        }}
      />,
    );
    expect(screen.queryByTestId("layer-info")).not.toBeInTheDocument();
  });
});
