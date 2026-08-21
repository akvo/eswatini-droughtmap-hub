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

// Mirrors what /risk-levels/{id} actually returns: the four scored exposure
// sub-indicators and nothing else. It used to carry a fifth `rainfed_cropland`
// row, which is why the Rain-fed tile's tests stayed green after the API
// stopped sending it (D-9) — a fixture that outlives its endpoint hides the
// very break it should catch.
const FULL_EXPOSURE = [
  { key: "population", value: 6420, norm: 0.35 },
  { key: "land_use_dvi_agri", value: 0.02, norm: 0.02 },
  // Null for all 59 Tinkhundla today — no cattle source; water demand covers
  // 45 of 59 and this Inkhundla is not one of them.
  { key: "cattle", value: null, norm: null },
  { key: "water_demand", value: null, norm: null },
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
  });

  it("renders no Rain-fed land use tile", () => {
    // Dropped with the exposure row that fed it (D-9). It was the only tile
    // reading an eligibility count, and re-sourcing it would have meant an
    // extra call to the IsAdmin-only /indicators/{id}.
    render(
      <CoverBlock {...props} risk={riskPayload({ exposure: FULL_EXPOSURE })} />,
    );
    expect(screen.queryByText("Rain-fed land use")).not.toBeInTheDocument();
    expect(screen.queryByText("hectares")).not.toBeInTheDocument();
    expect(screen.queryByText("1,037")).not.toBeInTheDocument();
  });

  it("does not tag a curated figure as a placeholder", () => {
    // `population` is a scored handover input and source.is_placeholder is
    // false here. With the prototype-sourced tile gone, nothing on the cover
    // carries the per-row provenance tag any more.
    render(
      <CoverBlock {...props} risk={riskPayload({ exposure: FULL_EXPOSURE })} />,
    );
    expect(screen.queryByText(/placeholder/i)).not.toBeInTheDocument();
  });

  it("tags People exposed when the risk row itself is seeded", () => {
    const payload = riskPayload({ exposure: FULL_EXPOSURE });
    payload.source.is_placeholder = true;
    render(<CoverBlock {...props} risk={payload} />);
    expect(screen.getAllByText(/placeholder/i)).toHaveLength(1);
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
    // Both remaining tiles empty at once — counting dashes would only track
    // how many tiles exist, which is not what this guards.
    render(
      <CoverBlock
        {...props}
        risk={riskPayload({ exposure: [], vulnerability: null })}
      />,
    );
    expect(screen.getAllByText("—")).toHaveLength(2);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });
});
