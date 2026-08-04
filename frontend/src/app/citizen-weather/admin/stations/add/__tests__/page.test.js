import { render, screen, waitFor } from "@testing-library/react";
import AddStationPage from "../page";
import { SENSOR_OPTIONS } from "@/static/mocks/citizen-weather";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("@/components", () => ({
  Can: ({ children }) => children,
  PageHeader: ({ title }) => <h1>{title}</h1>,
}));

// antd's dropdown needs a real layout engine to open in jsdom, and what
// matters here is which options we hand it — so render them inline.
jest.mock("antd", () => {
  const antd = jest.requireActual("antd");
  const Select = ({ options = [] }) => (
    <div>
      {options
        .flatMap((option) => option.options || [option])
        .map((option) => (
          <span key={option.value}>{option.label}</span>
        ))}
    </div>
  );
  return { ...antd, Select };
});

const mockApi = jest.fn();
jest.mock("@/lib", () => ({
  api: (...args) => mockApi(...args),
}));

const ADMINISTRATIONS = [
  { id: 1, name: "Big Bend", region: "Lubombo" },
  { id: 2, name: "Lobamba", region: "Hhohho" },
];

// The POST rejects any sensor key outside this set, and the observer form
// gates its inputs on the same keys — keep in step with backend CS_SENSORS
// (api/v1/v1_weather/constants.py).
describe("sensor keys", () => {
  it("matches the backend CS_SENSORS choices", () => {
    expect(SENSOR_OPTIONS.map((s) => s.key)).toEqual([
      "min_temp",
      "max_temp",
      "rain_gauge",
      "soil_moisture",
      "soil_temperature",
      "wind_speed",
    ]);
  });
});

describe("AddStationPage Inkhundla options", () => {
  beforeEach(() => {
    mockApi.mockReset();
    mockApi.mockImplementation((method, url) => {
      if (url === "/iks/administrations") {
        return Promise.resolve(ADMINISTRATIONS);
      }
      if (url === "/weather/citizen-science/stations") {
        // rows are keyed by administration_id — Big Bend is taken
        return Promise.resolve({ data: [{ key: 1 }] });
      }
      return Promise.resolve({});
    });
  });

  it("omits Inkhundla that already have an active observer", async () => {
    render(<AddStationPage />);

    await waitFor(() =>
      expect(screen.getByText("Lobamba")).toBeInTheDocument(),
    );
    expect(screen.queryByText("Big Bend")).not.toBeInTheDocument();
  });

  it("keeps every Inkhundla when no observer exists yet", async () => {
    mockApi.mockImplementation((method, url) =>
      url === "/iks/administrations"
        ? Promise.resolve(ADMINISTRATIONS)
        : Promise.resolve({ data: [] }),
    );
    render(<AddStationPage />);

    await waitFor(() =>
      expect(screen.getByText("Lobamba")).toBeInTheDocument(),
    );
    expect(screen.getByText("Big Bend")).toBeInTheDocument();
  });
});
