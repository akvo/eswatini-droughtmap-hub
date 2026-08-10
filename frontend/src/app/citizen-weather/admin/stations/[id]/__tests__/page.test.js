import { render, screen, waitFor } from "@testing-library/react";
import StationDetailPage from "../page";

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "7" }),
}));

jest.mock("@/components", () => ({
  Can: ({ children }) => children,
  PageHeader: ({ title, description }) => (
    <div>
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  ),
}));

jest.mock("@/components/CitizenWeather/NudgeModal", () => () => null);

const mockApi = jest.fn();
jest.mock("@/lib", () => ({
  api: (...args) => mockApi(...args),
  apiText: jest.fn(),
}));

const previousMonth = () => {
  const now = new Date();
  const d = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
};

const shiftMonth = (period, delta) => {
  const [year, month] = period.split("-").map(Number);
  const d = new Date(year, month - 1 + delta, 1);
  return {
    period: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`,
    label: d.toLocaleString("en-GB", { month: "short" }),
  };
};

const STATION = {
  key: 7,
  label: "Big Bend Primary",
  group: "Lubombo",
  sensors: ["rain_gauge", "min_temp"],
  observer: { id: 3, name: "Sipho", email: "sipho@example.org" },
  last_submission: previousMonth(),
  completeness: { reported: 6, of: 12 },
};

describe("StationDetailPage", () => {
  beforeEach(() => {
    mockApi.mockReset();
  });

  it("asks for the trailing window with the required period", async () => {
    mockApi.mockResolvedValue({ data: [STATION], history: [] });
    render(<StationDetailPage />);

    await waitFor(() => expect(mockApi).toHaveBeenCalledTimes(2));
    expect(mockApi).toHaveBeenCalledWith(
      "GET",
      `/weather/administrations/7/citizen-science?period=${previousMonth()}` +
        `&history=12`,
    );
  });

  it("derives month status from the station's own sensors", async () => {
    const latest = shiftMonth(previousMonth(), 0);
    const earlier = shiftMonth(previousMonth(), -1);
    mockApi.mockImplementation((_method, url) =>
      url.includes("citizen-science?period=")
        ? Promise.resolve({
            history: [
              // only the rain gauge reported -> partial
              {
                period: earlier.period,
                precipitation: 12,
                min_temperature: null,
              },
              { period: latest.period, precipitation: 30, min_temperature: 8 },
            ],
          })
        : Promise.resolve({ data: [STATION] }),
    );
    render(<StationDetailPage />);

    await waitFor(() =>
      expect(screen.getByText(latest.label)).toBeInTheDocument(),
    );
    expect(screen.getByText(latest.label)).toHaveStyle({
      background: "#12b76a",
    });
    expect(screen.getByText(earlier.label)).toHaveStyle({
      background: "#FAAD14",
    });
    // Months with no submitted reading stay misses, never fabricated.
    const missed = shiftMonth(previousMonth(), -5);
    expect(screen.getByText(missed.label)).toHaveStyle({
      background: "#eaecf0",
    });
  });

  it("shows an error state, not 'no observer', when the load fails", async () => {
    mockApi.mockRejectedValue(new Error("HTTP 500"));
    render(<StationDetailPage />);

    await waitFor(() =>
      expect(
        screen.getByText("Could not load this station"),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText("No observer assigned")).not.toBeInTheDocument();
  });
});
