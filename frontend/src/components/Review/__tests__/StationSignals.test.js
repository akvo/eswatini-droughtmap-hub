import { render, screen } from "@testing-library/react";
import { StationSignals, EsiPopover } from "../ReviewQueueTable";

const ESI = {
  satellite: 0.526,
  station_temp_anomaly: -4.1,
  comparable: false,
};

describe("StationSignals (WX-2b §12)", () => {
  it("signs the SPI delta but never the ESI rank", () => {
    render(<StationSignals stations={{ spi: 0.185, esi: ESI }} />);
    // SPI is a real difference, so it carries its sign. (0.185 is just under
    // 0.185 in float64, so toFixed(2) yields 0.18 — not a rounding bug.)
    expect(screen.getByText("+0.18")).toBeInTheDocument();
    // ESI is an absolute rank; a sign would read as a delta.
    expect(screen.getByText("0.53")).toBeInTheDocument();
    expect(screen.queryByText("+0.53")).toBeNull();
  });

  it("renders no unit after the ESI rank", () => {
    const { container } = render(
      <StationSignals stations={{ spi: null, esi: ESI }} />,
    );
    expect(container.textContent).not.toMatch(/°C/);
  });

  it("falls back to a dash when there is no ESI raster", () => {
    render(
      <StationSignals
        stations={{ spi: null, esi: { ...ESI, satellite: null } }}
      />,
    );
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});

describe("EsiPopover", () => {
  it("shows both halves and says they are not subtracted", () => {
    render(<EsiPopover esi={ESI} />);
    expect(screen.getByText("0.53")).toBeInTheDocument();
    expect(screen.getByText("-4.1 °C")).toBeInTheDocument();
    expect(screen.getByText(/never subtracted/i)).toBeInTheDocument();
    expect(screen.getByText(/30-year normal/i)).toBeInTheDocument();
  });

  it("signs a positive anomaly and dashes a missing one", () => {
    const { rerender } = render(
      <EsiPopover esi={{ ...ESI, station_temp_anomaly: 2.0 }} />,
    );
    expect(screen.getByText("+2.0 °C")).toBeInTheDocument();

    rerender(<EsiPopover esi={{ ...ESI, station_temp_anomaly: null }} />);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});
