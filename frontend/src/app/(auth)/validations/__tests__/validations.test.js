import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import ValidationsPage from "../page";
import { api } from "@/lib";
import { useRouter } from "next/navigation";

jest.setTimeout(30000);

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}));

jest.mock("@/lib", () => ({
  api: jest.fn(),
}));

// antd's responsive hooks reach for window.matchMedia, which jsdom lacks.
beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: jest.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
});

jest.mock("@/components", () => {
  const actual = jest.requireActual("@/components");
  return {
    ...actual,
    Can: ({ children }) => <>{children}</>,
    FeedbackSection: () => <div data-testid="feedback-section" />,
  };
});

// Server order: newest month first. Deadlines deliberately repeat, and the
// oldest deadline sits in the middle — a client-side sort on DEADLINE would
// move that row to the bottom and interleave the months.
const PUBLICATIONS = [
  { id: 320, year_month: "2026-05", due_date: "2026-07-31", status: 2 },
  { id: 316, year_month: "2026-04", due_date: "2026-07-31", status: 1 },
  { id: 319, year_month: "2000-04", due_date: "2026-07-25", status: 1 },
  { id: 318, year_month: "2000-03", due_date: "2026-07-31", status: 1 },
  { id: 317, year_month: "2000-02", due_date: "2026-07-31", status: 3 },
];

describe("ValidationsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useRouter.mockReturnValue({ push: jest.fn() });
    api.mockResolvedValue({ data: PUBLICATIONS, total: PUBLICATIONS.length });
  });

  it("renders the rows in the order the server returned them", async () => {
    render(<ValidationsPage />);
    await waitFor(() => expect(api).toHaveBeenCalled());

    const rows = await screen.findAllByRole("row");
    // row 0 is the header
    const months = rows
      .slice(1)
      .map((row) => within(row).getAllByRole("cell")[1].textContent);

    expect(months).toEqual([
      "May 2026",
      "April 2026",
      "April 2000",
      "March 2000",
      "February 2000",
    ]);
  });
});
