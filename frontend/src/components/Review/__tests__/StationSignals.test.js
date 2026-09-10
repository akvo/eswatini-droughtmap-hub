import { render, screen } from "@testing-library/react";
import { StationSignals } from "../ReviewQueueTable";

describe("StationSignals", () => {
  it("renders the signed LST delta in °C next to the SPI delta", () => {
    render(
      <StationSignals stations={{ spi: -0.26, lst: 0.8, lst_reason: null }} />,
    );
    expect(screen.getByText("-0.26")).toBeInTheDocument();
    expect(screen.getByText("+0.80 °C")).toBeInTheDocument();
  });

  it("keeps the em-dash and the reason tooltip when LST is absent", () => {
    render(
      <StationSignals
        stations={{
          spi: 0.1,
          lst: null,
          lst_reason: "no_satellite_temperature",
        }}
      />,
    );
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(
      screen.getByTitle(/satellite temperature for this month/),
    ).toBeInTheDocument();
  });

  it("never renders a null delta as zero", () => {
    render(<StationSignals stations={undefined} />);
    expect(screen.queryByText(/0\.00/)).not.toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(2);
  });
});
