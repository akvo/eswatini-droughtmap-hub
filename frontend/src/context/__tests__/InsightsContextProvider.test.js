import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import InsightsContextProvider, {
  useInsights,
} from "../InsightsContextProvider";
import { api } from "../../lib/api";

// Alias paths do not resolve inside jest.mock — same relative form as IksTab.
jest.mock("../../lib/api", () => ({
  api: jest.fn(),
}));

const ADMINISTRATIONS = [
  { id: 4588078, name: "Hhukwini", region: "Hhohho", zone: "middleveld" },
  { id: 2042786, name: "Kwaluseni", region: "Manzini", zone: "lowveld" },
];

const Probe = () => {
  const {
    selectedInkhundla,
    administrationId,
    region,
    zone,
    setSelectedInkhundla,
  } = useInsights();
  return (
    <div>
      <span data-testid="selected">{String(selectedInkhundla)}</span>
      <span data-testid="administration-id">{String(administrationId)}</span>
      <span data-testid="region">{region}</span>
      <span data-testid="zone">{zone}</span>
      <button onClick={() => setSelectedInkhundla("Hhukwini")}>pick</button>
    </div>
  );
};

const renderProvider = () =>
  render(
    <InsightsContextProvider>
      <Probe />
    </InsightsContextProvider>,
  );

describe("InsightsContextProvider", () => {
  beforeEach(() => {
    api.mockResolvedValue(ADMINISTRATIONS);
  });

  it("opens with nothing selected so the shell can show its empty state", async () => {
    renderProvider();

    await waitFor(() => {
      expect(api).toHaveBeenCalledWith("GET", "/iks/administrations");
    });
    expect(screen.getByTestId("selected")).toHaveTextContent("null");
    // No selection must resolve to no administration rather than throwing on
    // selectedInkhundla.toLowerCase() — that would crash the page on load.
    expect(screen.getByTestId("administration-id")).toHaveTextContent("null");
    expect(screen.getByTestId("region")).toBeEmptyDOMElement();
    expect(screen.getByTestId("zone")).toBeEmptyDOMElement();
  });

  it("resolves the administration record once one is picked", async () => {
    renderProvider();
    await waitFor(() => {
      expect(api).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByText("pick"));

    await waitFor(() => {
      expect(screen.getByTestId("administration-id")).toHaveTextContent(
        "4588078",
      );
    });
    expect(screen.getByTestId("region")).toHaveTextContent("Hhohho");
    expect(screen.getByTestId("zone")).toHaveTextContent("middleveld");
  });
});
