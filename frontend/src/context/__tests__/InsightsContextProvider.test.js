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
    setAdministrationId,
  } = useInsights();
  return (
    <div>
      <span data-testid="selected">{String(selectedInkhundla)}</span>
      <span data-testid="administration-id">{String(administrationId)}</span>
      <span data-testid="region">{region}</span>
      <span data-testid="zone">{zone}</span>
      {/* The dropdown sets the id; everything else is derived from it.
          Picks the SECOND admin so it differs from the auto-defaulted first. */}
      <button onClick={() => setAdministrationId(2042786)}>pick</button>
      <button onClick={() => setAdministrationId(null)}>clear</button>
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

  it("defaults to the first inkhundla once the list loads", async () => {
    renderProvider();

    // First admin in the list, resolved by id — not a hardcoded value.
    await waitFor(() => {
      expect(screen.getByTestId("administration-id")).toHaveTextContent(
        "4588078",
      );
    });
    expect(screen.getByTestId("selected")).toHaveTextContent("Hhukwini");
    expect(screen.getByTestId("region")).toHaveTextContent("Hhohho");
    expect(screen.getByTestId("zone")).toHaveTextContent("middleveld");
  });

  it("shows the empty state until the list arrives, without crashing", async () => {
    let resolveAdmins;
    api.mockReturnValue(
      new Promise((resolve) => {
        resolveAdmins = resolve;
      }),
    );
    renderProvider();

    // Before the fetch resolves: nothing selected, nothing derived, no throw.
    expect(screen.getByTestId("administration-id")).toHaveTextContent("null");
    expect(screen.getByTestId("selected")).toHaveTextContent("null");
    expect(screen.getByTestId("region")).toBeEmptyDOMElement();

    resolveAdmins(ADMINISTRATIONS);

    await waitFor(() => {
      expect(screen.getByTestId("selected")).toHaveTextContent("Hhukwini");
    });
  });

  it("derives the name, region and zone when another inkhundla is picked", async () => {
    renderProvider();
    await waitFor(() => {
      expect(screen.getByTestId("selected")).toHaveTextContent("Hhukwini");
    });

    fireEvent.click(screen.getByText("pick")); // -> 2042786 / Kwaluseni

    await waitFor(() => {
      expect(screen.getByTestId("administration-id")).toHaveTextContent(
        "2042786",
      );
    });
    expect(screen.getByTestId("selected")).toHaveTextContent("Kwaluseni");
    expect(screen.getByTestId("region")).toHaveTextContent("Manzini");
    expect(screen.getByTestId("zone")).toHaveTextContent("lowveld");
  });

  it("clears back to the empty state without re-defaulting", async () => {
    renderProvider();
    await waitFor(() => {
      expect(screen.getByTestId("selected")).toHaveTextContent("Hhukwini");
    });

    // The auto-default fires once, on load — clearing afterwards must stick.
    fireEvent.click(screen.getByText("clear"));

    await waitFor(() => {
      expect(screen.getByTestId("administration-id")).toHaveTextContent("null");
    });
    expect(screen.getByTestId("selected")).toHaveTextContent("null");
    expect(screen.getByTestId("region")).toBeEmptyDOMElement();
  });
});
