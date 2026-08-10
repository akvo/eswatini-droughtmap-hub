import React from "react";
import { render, screen } from "@testing-library/react";
import CoverBlock from "../sections/CoverBlock";
import ExposureBars from "../sections/ExposureBars";

// The mocks are gone (BB-3): every figure below comes from the
// /risk-levels/{id} payload useBriefData already holds. These tests exist to
// pin the one rule that made un-mocking safe — a missing value renders as
// missing, never as zero.
const riskPayload = ({ exposure = [], vulnerability = 0.3, area = 450.8 }) => ({
  administration: {
    id: 4387750,
    name: "Kubuta",
    region: "Shiselweni",
    zone: "upper_middleveld",
    area_km2: area,
  },
  exposure: { data: exposure, value: 0.2 },
  vulnerability: { value: vulnerability },
  source: { is_placeholder: false },
});

const FULL_EXPOSURE = [
  { key: "population", value: 6420, norm: 0.35 },
  { key: "land_use_dvi_agri", value: 0.02, norm: 0.02 },
  // Null for all 59 Tinkhundla today — no DWA load, no cattle source.
  { key: "cattle", value: null, norm: null },
  { key: "water_demand", value: null, norm: null },
  {
    key: "rainfed_cropland",
    value: 1037,
    norm: null,
    // Eligibility counts come from the prototype CSV, not the NDMA handover
    // workbook that fills the scored risk inputs.
    meta: { source: "prototype-illustrative" },
  },
];

describe("ExposureBars", () => {
  it("renders each norm as a percentage", () => {
    render(<ExposureBars risk={riskPayload({ exposure: FULL_EXPOSURE })} />);
    expect(screen.getByText("35%")).toBeInTheDocument();
    expect(screen.getByText("30%")).toBeInTheDocument(); // susceptibility
  });

  it("renders a null norm as No data, never 0%", () => {
    render(<ExposureBars risk={riskPayload({ exposure: FULL_EXPOSURE })} />);
    // cattle + water_demand are both null today.
    expect(screen.getAllByText("No data")).toHaveLength(2);
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });

  it("survives a missing risk payload without crashing or inventing zeros", () => {
    render(<ExposureBars risk={null} />);
    expect(screen.getAllByText("No data")).toHaveLength(5);
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });
});

describe("CoverBlock", () => {
  const props = {
    showHeader: true,
    showTiles: true,
    name: "Kubuta",
    region: "Shiselweni",
    zone: "upper_middleveld",
    cdi: null,
  };

  it("reads the absolutes and the area off the risk payload", () => {
    render(
      <CoverBlock {...props} risk={riskPayload({ exposure: FULL_EXPOSURE })} />,
    );
    expect(screen.getByText("450.8 km²")).toBeInTheDocument();
    expect(screen.getByText("6,420")).toBeInTheDocument();
    expect(screen.getByText("1,037")).toBeInTheDocument();
  });

  it("tags the two tiles by their own provenance, not one shared flag", () => {
    // population is a scored handover input and source.is_placeholder is
    // false here, so People exposed must NOT be tagged; rainfed_cropland
    // carries its own prototype provenance, so it must be.
    render(
      <CoverBlock {...props} risk={riskPayload({ exposure: FULL_EXPOSURE })} />,
    );
    const tags = screen.getAllByText(/placeholder/i);
    expect(tags).toHaveLength(1);
  });

  it("renders no Total land tile", () => {
    render(
      <CoverBlock {...props} risk={riskPayload({ exposure: FULL_EXPOSURE })} />,
    );
    expect(screen.queryByText("Total land")).not.toBeInTheDocument();
  });

  it("omits the area entirely when it is null, rather than showing 0", () => {
    render(
      <CoverBlock
        {...props}
        risk={riskPayload({ exposure: FULL_EXPOSURE, area: null })}
      />,
    );
    expect(screen.queryByText(/km²/)).not.toBeInTheDocument();
  });

  it("renders an em dash for every figure when there is no Indicator row", () => {
    render(<CoverBlock {...props} risk={riskPayload({ exposure: [] })} />);
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });
});
