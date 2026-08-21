import { render, screen, within } from "@testing-library/react";
import InkhundlaMap, { MARKER_TYPES } from "../InkhundlaMap";

// Leaflet needs a DOM jsdom cannot give it, so the map is a seam: the mock
// hands back the two arguments DynamicMap really passes — ReactLeaflet and
// Leaflet — and records the icon options each Marker was built with.
const markers = [];

jest.mock("next/dynamic", () => () => {
  const MockMap = ({ children }) => (
    <div data-testid="base-map">
      {children(
        {
          GeoJSON: () => <div data-testid="geojson-layer" />,
          Marker: ({ icon, children: kids }) => (
            <div data-testid="marker" data-html={icon.html}>
              {kids}
            </div>
          ),
          Tooltip: ({ children: kids }) => <span>{kids}</span>,
          useMap: () => ({ fitBounds: jest.fn() }),
        },
        {
          divIcon: (opts) => {
            markers.push(opts);
            return opts;
          },
        },
      )}
    </div>
  );
  return MockMap;
});

jest.mock("@/context/AppContextProvider", () => ({
  useAppContext: () => ({
    geoData: {
      features: [
        {
          properties: { administration_id: 1 },
          geometry: {
            type: "Polygon",
            coordinates: [
              [
                [31, -26],
                [32, -27],
              ],
            ],
          },
        },
      ],
    },
  }),
}));

const station = { lat: -26.5, lon: 31.5, name: "Mbabane station" };
const iks = [{ lat: -26.6, lon: 31.6 }];

beforeEach(() => {
  markers.length = 0;
});

describe("InkhundlaMap markers", () => {
  it("gives the weather station and the IKS pin different icons", () => {
    render(
      <InkhundlaMap
        administrationId="1"
        stationMarker={station}
        iksMarkers={iks}
      />,
    );

    expect(markers).toHaveLength(2);
    const [stationIcon, iksIcon] = markers;
    // The whole point: the two must not render the same pin.
    expect(stationIcon.html).not.toEqual(iksIcon.html);
    expect(stationIcon.html).toContain(MARKER_TYPES.station.color);
    expect(iksIcon.html).toContain(MARKER_TYPES.iks.color);
  });

  it("distinguishes them by glyph, not colour alone", () => {
    render(
      <InkhundlaMap
        administrationId="1"
        stationMarker={station}
        iksMarkers={iks}
      />,
    );

    const [stationIcon, iksIcon] = markers;
    // Strip the colours, and the two must STILL differ — otherwise the map
    // is unreadable to anyone who cannot separate the two hues.
    const decolour = (html) =>
      html
        .split(MARKER_TYPES.station.color)
        .join("")
        .split(MARKER_TYPES.iks.color)
        .join("");
    expect(decolour(stationIcon.html)).not.toEqual(decolour(iksIcon.html));
  });

  it("names the station in its tooltip, falling back to the type label", () => {
    const { rerender } = render(
      <InkhundlaMap administrationId="1" stationMarker={station} />,
    );
    expect(screen.getByText("Mbabane station")).toBeInTheDocument();

    rerender(
      <InkhundlaMap
        administrationId="1"
        stationMarker={{ ...station, name: null }}
      />,
    );
    expect(screen.getAllByText("Weather station").length).toBeGreaterThan(0);
  });

  it("lists only the marker kinds actually on the map", () => {
    // Scoped to the legend: both labels also appear in marker tooltips.
    const legend = () => within(screen.getByTestId("marker-legend"));

    const { rerender } = render(
      <InkhundlaMap administrationId="1" stationMarker={station} />,
    );
    expect(legend().getByText("Weather station")).toBeInTheDocument();
    expect(legend().queryByText("IKS observation")).not.toBeInTheDocument();

    rerender(<InkhundlaMap administrationId="1" iksMarkers={iks} />);
    expect(legend().getByText("IKS observation")).toBeInTheDocument();
    expect(legend().queryByText("Weather station")).not.toBeInTheDocument();
  });

  it("renders no legend when the Inkhundla has neither", () => {
    render(<InkhundlaMap administrationId="1" />);
    expect(screen.queryByTestId("marker-legend")).not.toBeInTheDocument();
    expect(markers).toHaveLength(0);
  });
});
