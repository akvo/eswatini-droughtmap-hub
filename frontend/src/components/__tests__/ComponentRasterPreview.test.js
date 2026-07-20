import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import ComponentRasterPreview from "../ComponentRasterPreview";
import { api } from "@/lib";

jest.mock("@/lib", () => ({ api: jest.fn() }));

// antd's responsive hooks reach for window.matchMedia, which jsdom lacks.
jest.mock("antd/lib/_util/responsiveObserver", () => {
  const mockObserver = {
    subscribe: jest.fn((cb) => {
      cb({ xs: true, sm: true, md: true, lg: true, xl: true, xxl: true });
      return { unsubscribe: jest.fn() };
    }),
    unsubscribe: jest.fn(),
    register: jest.fn(),
    unregister: jest.fn(),
  };
  const fn = jest.fn(() => mockObserver);
  fn.default = mockObserver;
  Object.assign(fn, mockObserver);
  return fn;
});

const components = (unavailable = null) => ({
  data: [
    { key: "esi", label: "ESI Raster Map", geonode_id: 201 },
    { key: "evi2", label: "EVI2 Raster Map", geonode_id: 202 },
    { key: "sm", label: "SM Raster Map", geonode_id: 203 },
    { key: "spi", label: "SPI Raster Map", geonode_id: 204 },
  ].map((c) => ({ ...c, available: c.key !== unavailable })),
});

describe("ComponentRasterPreview", () => {
  beforeEach(() => jest.clearAllMocks());

  it("lists the components GeoNode has for the selected month", async () => {
    api.mockResolvedValue(components());

    render(<ComponentRasterPreview yearMonth="2026-04-01" />);

    await waitFor(() =>
      expect(screen.getByText("ESI Raster Map")).toBeInTheDocument(),
    );
    expect(api).toHaveBeenCalledWith(
      "GET",
      "/admin/component-rasters?year_month=2026-04",
    );
    expect(screen.getByText("SPI Raster Map")).toBeInTheDocument();
    // Nothing missing, so no explanatory notice.
    expect(screen.queryByText(/attached automatically/)).toBeNull();
  });

  it("flags a missing component and explains it is not an error", async () => {
    api.mockResolvedValue(components("spi"));

    render(<ComponentRasterPreview yearMonth="2026-04-01" />);

    await waitFor(() =>
      expect(
        screen.getByText(/SPI Raster Map — not available/),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText(/attached automatically/)).toBeInTheDocument();
  });

  it("degrades to 'No data' when the lookup fails", async () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    api.mockRejectedValue(new Error("geonode down"));

    render(<ComponentRasterPreview yearMonth="2026-04-01" />);

    await waitFor(() =>
      expect(screen.getByText("No data")).toBeInTheDocument(),
    );
    expect(screen.queryByText(/attached automatically/)).toBeNull();
  });

  it("does not call the API without a month", () => {
    render(<ComponentRasterPreview yearMonth={null} />);

    expect(api).not.toHaveBeenCalled();
  });
});
