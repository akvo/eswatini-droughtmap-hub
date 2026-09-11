import {
  render,
  screen,
  fireEvent,
  act,
  waitFor,
} from "@testing-library/react";
import { message } from "antd";
import dayjs from "dayjs";
import HeroSection from "../HeroSection";

// Swapped per test: null exercises the no-provider path, an object exercises
// the D-9 expand/collapse handshake.
let printContext = null;
jest.mock("@/context/PrintContextProvider", () => ({
  usePrintContext: () => printContext,
}));

// Mock matchMedia for Ant Design responsiveness in JSDOM tests
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

// Shape mirrors GET /api/v1/insights/hero.
const hero = {
  status: { category: 3, label: "Severe Drought" },
  period: "2026-05",
  published: "13 Aug 2026",
  nextUpdate: "13 Sep 2026",
  headline: "Drought situation overview — May 2026",
  summary: "<p>Severe conditions across the lowveld.</p>",
};

const ORIGINAL_TITLE = "Eswatini Drought Intelligence Hub";

// The handler awaits the sections (D-9) and then a frame (D-5), so timer
// advances and microtask flushes have to interleave — a single advance runs
// before the first await has even resolved.
const flush = async (rounds = 3) => {
  for (let i = 0; i < rounds; i += 1) {
    // eslint-disable-next-line no-await-in-loop
    await act(async () => {
      jest.advanceTimersByTime(32);
    });
  }
};

const clickDownload = async () => {
  fireEvent.click(
    screen.getByRole("button", { name: /Download National Overview/i }),
  );
  await flush();
};

describe("HeroSection — PDF export (INS-PDF-1)", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    printContext = null;
    document.title = ORIGINAL_TITLE;
    window.print = jest.fn();
    jest.spyOn(message, "error").mockImplementation(() => {});
    jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    // The tooltip test opts back into real timers, so only drain if still fake.
    if (jest.isMockFunction(setTimeout)) {
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
    }
    jest.restoreAllMocks();
  });

  it("names the file from the CDI period, not today", async () => {
    render(<HeroSection hero={hero} />);
    await clickDownload();

    expect(window.print).toHaveBeenCalledTimes(1);
    expect(document.title).toBe("National_Drought_overview_2026-05.pdf");
  });

  it("falls back to the current month when the period is missing", async () => {
    render(<HeroSection hero={{ ...hero, period: null }} />);
    await clickDownload();

    expect(document.title).toBe(
      `National_Drought_overview_${dayjs().format("YYYY-MM")}.pdf`,
    );
  });

  it("rejects a malformed period rather than putting it in the filename", async () => {
    // Guards §8: document.title must not take an arbitrary server string.
    render(<HeroSection hero={{ ...hero, period: "../../etc/passwd" }} />);
    await clickDownload();

    expect(document.title).toBe(
      `National_Drought_overview_${dayjs().format("YYYY-MM")}.pdf`,
    );
  });

  it("restores the title and re-enables the button after printing", async () => {
    render(<HeroSection hero={hero} />);
    await clickDownload();

    // afterprint fires on cancel as well as completion.
    await act(async () => {
      window.dispatchEvent(new Event("afterprint"));
    });

    expect(document.title).toBe(ORIGINAL_TITLE);
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Download National Overview/i }),
      ).not.toBeDisabled();
    });
  });

  it("toasts and recovers when print() throws", async () => {
    window.print = jest.fn(() => {
      throw new Error("print unavailable");
    });
    render(<HeroSection hero={hero} />);
    await clickDownload();

    expect(message.error).toHaveBeenCalledWith(
      "Failed to download PDF. Please try again.",
    );
    expect(document.title).toBe(ORIGINAL_TITLE);
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Download National Overview/i }),
      ).not.toBeDisabled();
    });
  });

  it("waits for the sections to expand before printing", async () => {
    // The whole point of D-9: printing before the layer maps have mounted
    // would produce a PDF missing every extra tab.
    let releaseSections;
    const expandForPrint = jest.fn(
      () => new Promise((resolve) => (releaseSections = resolve)),
    );
    const collapse = jest.fn();
    printContext = { expandForPrint, collapse };

    render(<HeroSection hero={hero} />);
    await clickDownload();

    expect(expandForPrint).toHaveBeenCalled();
    expect(window.print).not.toHaveBeenCalled();

    releaseSections();
    await flush();

    expect(window.print).toHaveBeenCalledTimes(1);
  });

  it("collapses the print-only content again afterwards", async () => {
    const collapse = jest.fn();
    printContext = { expandForPrint: jest.fn().mockResolvedValue(), collapse };

    render(<HeroSection hero={hero} />);
    await clickDownload();
    await act(async () => {
      window.dispatchEvent(new Event("afterprint"));
    });

    expect(collapse).toHaveBeenCalled();
  });

  it("shows the tooltip on hover", async () => {
    jest.useRealTimers();
    render(<HeroSection hero={hero} />);

    fireEvent.mouseEnter(
      screen.getByRole("button", { name: /Download National Overview/i }),
    );

    expect(
      await screen.findByText("Download full page as PDF"),
    ).toBeInTheDocument();
  });
});
