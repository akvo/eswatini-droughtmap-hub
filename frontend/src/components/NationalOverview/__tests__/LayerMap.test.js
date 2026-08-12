import { render, screen, waitFor } from "@testing-library/react";
import LayerMap from "../LayerMap";

// The Leaflet components only matter here as "did the right render mode get
// chosen" markers — the map itself needs a DOM Leaflet cannot have in jsdom.
jest.mock("@/components/Map/CDIMap", () => {
  const MockCDIMap = ({ children, onFeature }) => (
    <div data-testid="choropleth-map">
      {/* Exercises the colour function so a broken ramp fails here, not
          silently in the browser. */}
      <span data-testid="sample-fill">
        {JSON.stringify(
          onFeature?.({ properties: { administration_id: 1 } }) || {},
        )}
      </span>
      {/* A second, unselected feature — the outline must apply to one only. */}
      <span data-testid="other-fill">
        {JSON.stringify(
          onFeature?.({ properties: { administration_id: 2 } }) || {},
        )}
      </span>
      {children}
    </div>
  );
  return MockCDIMap;
});

// react-compare-slider is ESM-only (no `main`, no `require` condition), so
// Jest's CJS resolver cannot load it — webpack can, which is why the app is
// fine. `virtual` sidesteps resolution entirely. Testing a third-party
// slider's internals is not this suite's job; that both sides get handed to
// it is.
jest.mock(
  "react-compare-slider",
  () => ({
    ReactCompareSlider: ({ itemOne, itemTwo }) => (
      <div data-testid="compare-slider">
        {itemOne}
        {itemTwo}
      </div>
    ),
  }),
  { virtual: true },
);

jest.mock("@/components/Map", () => ({
  Map: ({ children }) => (
    <div data-testid="base-map">
      {children({
        GeoJSON: () => <div data-testid="geojson-layer" />,
      })}
    </div>
  ),
}));

const choropleth = {
  key: "population",
  label: "Population map",
  type: "choropleth",
  data: [{ administration_id: 1, value: 24310 }],
  legend: {
    unit: "people",
    min: 0,
    max: 80000,
    continuous: true,
    colors: ["#FDE0EF", "#8E0152"],
  },
  meta: { source: "Handover", asOf: null },
};

describe("LayerMap render modes", () => {
  it("renders a choropleth and paints a value from the ramp", () => {
    render(<LayerMap layer={choropleth} />);
    expect(screen.getByTestId("choropleth-map")).toBeInTheDocument();
    const fill = JSON.parse(screen.getByTestId("sample-fill").textContent);
    expect(fill.fillColor).toMatch(/^#/);
    expect(fill.fillOpacity).toBeGreaterThan(0.5);
  });

  it("leaves an Inkhundla with no value visibly unpainted", () => {
    render(<LayerMap layer={{ ...choropleth, data: [] }} />);
    const fill = JSON.parse(screen.getByTestId("sample-fill").textContent);
    expect(fill.fillOpacity).toBeLessThan(0.5);
  });

  it("paints a drought-scheme layer from the frontend palette", () => {
    render(
      <LayerMap
        layer={{
          key: "regions",
          label: "Regions",
          type: "choropleth",
          // D2 Severe Drought — the API sends the category, never the hex.
          data: [
            {
              administration_id: 1,
              value: 3,
              group: "Lubombo",
              confidence: 100,
            },
          ],
          legend: { scheme: "drought" },
        }}
      />,
    );
    const fill = JSON.parse(screen.getByTestId("sample-fill").textContent);
    expect(fill.fillColor).toBe("#ffaa00");
  });

  it("renders precipitation as a choropleth, not a raster overlay", () => {
    // A bbox raster at national zoom had no borders to locate it against and
    // read as texture, so millimetres are painted on the Tinkhundla instead.
    render(
      <LayerMap
        layer={{
          key: "precipitation",
          label: "Precipitation",
          type: "choropleth",
          data: [{ administration_id: 1, value: 8.3 }],
          legend: {
            unit: "mm",
            min: 4.6,
            max: 11.1,
            continuous: true,
            colors: ["#F7FBFF", "#08306B"],
          },
        }}
      />,
    );
    expect(screen.getByTestId("choropleth-map")).toBeInTheDocument();
    const fill = JSON.parse(screen.getByTestId("sample-fill").textContent);
    expect(fill.fillColor).toMatch(/^#/);
  });

  it("fetches its geometry for a vector layer", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({ type: "FeatureCollection", features: [] }),
      }),
    );
    render(
      <LayerMap
        layer={{
          key: "agro-eco",
          label: "Agro-ecological zones",
          type: "vector",
          url: "/api/v1/insights/geo/agro-eco",
          property: "LEVEL1",
          legend: {
            categories: [{ key: "HV", label: "Highveld", color: "#2E7D32" }],
          },
        }}
      />,
    );
    await waitFor(() =>
      expect(screen.getByTestId("geojson-layer")).toBeInTheDocument(),
    );
    expect(global.fetch).toHaveBeenCalledWith("/api/v1/insights/geo/agro-eco");
  });

  it("outlines the selected Inkhundla and no other", () => {
    render(<LayerMap layer={choropleth} selectedInkhundlaId={1} />);
    const selected = JSON.parse(
      screen.getAllByTestId("sample-fill")[0].textContent,
    );
    const other = JSON.parse(
      screen.getAllByTestId("other-fill")[0].textContent,
    );
    expect(selected.weight).toBe(3);
    expect(selected.color).toBe("#111827");
    // Raised, or later siblings overdraw half the border.
    expect(selected.bringToFront).toBe(true);
    expect(other.weight).toBeUndefined();
  });

  it("drops the outline when the filter is cleared", () => {
    render(<LayerMap layer={choropleth} selectedInkhundlaId={null} />);
    const fill = JSON.parse(screen.getByTestId("sample-fill").textContent);
    expect(fill.weight).toBeUndefined();
  });

  it("outlines the selection on both sides of a comparison", () => {
    render(
      <LayerMap
        layer={choropleth}
        compareLayer={{ ...choropleth, key: "population-compare" }}
        selectedInkhundlaId={1}
      />,
    );
    screen.getAllByTestId("sample-fill").forEach((node) => {
      expect(JSON.parse(node.textContent).weight).toBe(3);
    });
  });

  it("renders both months side by side when comparing", () => {
    render(
      <LayerMap
        layer={choropleth}
        compareLayer={{ ...choropleth, key: "population-compare" }}
      />,
    );
    expect(screen.getAllByTestId("choropleth-map")).toHaveLength(2);
  });

  it("renders the reason for an empty layer", () => {
    render(
      <LayerMap
        layer={{
          key: "precipitation",
          label: "Precipitation",
          type: "empty",
          reason: "No CHIRPS rainfall raster stored for 2026-07.",
        }}
      />,
    );
    expect(screen.getByText(/No data to display/)).toBeInTheDocument();
    expect(screen.getByText(/No CHIRPS rainfall raster/)).toBeInTheDocument();
  });

  it("degrades instead of crashing on a render mode it does not know", () => {
    // The backend can grow a type before the frontend ships support for it.
    render(<LayerMap layer={{ key: "future", type: "hologram" }} />);
    expect(screen.getByText(/No data to display/)).toBeInTheDocument();
  });
});
