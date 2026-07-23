import React from "react";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { Modal } from "antd";
import { api } from "@/lib";
import ValidationDetailPage from "../page";

jest.setTimeout(30000);

jest.mock("@/lib", () => ({ api: jest.fn() }));

// <Can> gates on CASL abilities loaded from the session; render children.
jest.mock("@/components", () => ({
  Can: ({ children }) => <>{children}</>,
  FeedbackSection: () => null,
  TabButtons: ({ options, value, onChange }) => (
    <div>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  ),
}));

jest.mock("@/components/Validation", () => ({
  PublishModal: () => null,
  ReviewerPanelModal: () => null,
}));

jest.mock("@/components/DS", () => ({
  MetricCard: ({ label, value, onClick, active }) =>
    onClick ? (
      <button type="button" aria-pressed={active} onClick={onClick}>
        {label}: {value}
      </button>
    ) : (
      <div>
        {label}: {value}
      </div>
    ),
  // The real chip reads DROUGHT_CATEGORY_CODE; stub the code so the D-class
  // assertions stay about the page, not about the design-system component.
  DroughtScore: ({ level }) => (
    <span>{["Normal", "D0", "D1", "D2", "D3", "D4"][level]}</span>
  ),
}));

const replace = jest.fn();
const push = jest.fn();
let currentParams = new URLSearchParams();

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "4" }),
  useRouter: () => ({ replace, push }),
  usePathname: () => "/validations/4",
  useSearchParams: () => currentParams,
}));

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

const STATS = {
  meta: {
    publication_id: 4,
    year_month: "2026-05",
    published_at: null,
    total: 59,
    reviewers_required: 5,
    can_publish: false,
    pending_validation: 12,
  },
  data: [
    { key: "ready", label: "Ready for validation", value: 7, meta: "" },
    { key: "disagreement", label: "High disagreement", value: 3, meta: "" },
    { key: "validated", label: "Validated this period", value: 2, meta: "" },
    { key: "awaiting", label: "Awaits reviews", value: 50, meta: "" },
  ],
};

const ROW = {
  administration_id: 12,
  label: "Kubuta",
  group: "Shiselweni",
  reviews_completed: 4,
  reviews_total: 5,
  reviewers: [{ id: 7, label: "AR", group: 3 }],
  dclass_spread: [3],
  consensus: 80,
  status: "awaiting",
  awaiting_count: 1,
  validated_category: null,
};

const respond = (rows = [ROW], total = 59) =>
  api.mockImplementation((_method, url) =>
    Promise.resolve(
      url.includes("/stats") ? STATS : { data: rows, total, current: 1 },
    ),
  );

const renderPage = async () => {
  const result = render(<ValidationDetailPage />);
  await screen.findByText("Kubuta");
  return result;
};

const urlsRequested = () =>
  api.mock.calls
    .map(([, url]) => url)
    .filter((url) => url.includes("/administrations"));

beforeEach(() => {
  currentParams = new URLSearchParams();
  replace.mockClear();
  push.mockClear();
  respond();
});

// Modal.confirm renders imperatively into document.body, outside the React
// tree RTL cleans up. A dialog left open by one test is otherwise still there
// for the next one to find — and click.
afterEach(() => {
  Modal.destroyAll();
  cleanup();
  document.body.innerHTML = "";
});

describe("Validation queue page", () => {
  it("reads filters from the URL and sends them to the server", async () => {
    currentParams = new URLSearchParams("status=ready&search=kub&page=2");
    await renderPage();

    await waitFor(() => expect(urlsRequested()).toHaveLength(1));
    const url = urlsRequested()[0];
    expect(url).toContain("page=2");
    expect(url).toContain("status=ready");
    expect(url).toContain("search=kub");
  });

  it("writes the status tab into the URL and resets to page 1", async () => {
    currentParams = new URLSearchParams("page=3");
    await renderPage();
    await waitFor(() => expect(urlsRequested()).toHaveLength(1));

    fireEvent.click(screen.getByRole("button", { name: "Validated" }));

    await waitFor(() => expect(replace).toHaveBeenCalled());
    const next = replace.mock.calls.at(-1)[0];
    expect(next).toContain("status=validated");
    expect(next).toContain("page=1");
  });

  it("debounces typing into ?search= and resets to page 1", async () => {
    jest.useFakeTimers();
    try {
      await renderPage();
      const input = screen.getByPlaceholderText("Search");

      fireEvent.change(input, { target: { value: "k" } });
      fireEvent.change(input, { target: { value: "ku" } });
      fireEvent.change(input, { target: { value: "kub" } });
      // Nothing written yet — that is the point of the debounce.
      expect(replace).not.toHaveBeenCalled();

      jest.advanceTimersByTime(400);
      expect(replace).toHaveBeenCalledTimes(1);
      const next = replace.mock.calls[0][0];
      expect(next).toContain("search=kub");
      expect(next).toContain("page=1");
    } finally {
      jest.useRealTimers();
    }
  });

  it("paginates on the server total, not the rows it was handed", async () => {
    // One row on the page but 59 in the publication: the pager must still
    // render, which it would not if it counted data.length.
    await renderPage();
    await waitFor(() => expect(urlsRequested()).toHaveLength(1));

    await waitFor(() => expect(screen.getByTitle("2")).toBeInTheDocument());
  });

  it("disables Publish until the server says every Inkhundla is validated", async () => {
    await renderPage();
    await waitFor(() => expect(urlsRequested()).toHaveLength(1));

    expect(
      screen.getByRole("button", { name: /publish validated map/i }),
    ).toBeDisabled();
  });

  it("enables Publish when can_publish is true", async () => {
    api.mockImplementation((_method, url) =>
      Promise.resolve(
        url.includes("/stats")
          ? {
              ...STATS,
              meta: { ...STATS.meta, can_publish: true, pending_validation: 0 },
            }
          : { data: [ROW], total: 59, current: 1 },
      ),
    );
    await renderPage();
    await waitFor(() => expect(urlsRequested()).toHaveLength(1));

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /publish validated map/i }),
      ).not.toBeDisabled(),
    );
  });

  it("shows the admin's final D-class beside a validated badge", async () => {
    // The spread column shows what reviewers submitted; the outcome of a
    // validated row would otherwise be invisible without opening it.
    respond([
      { ...ROW, status: "validated", awaiting_count: 0, validated_category: 3 },
    ]);
    await renderPage();

    // Assert the thing itself inside waitFor. Gating on a different element
    // and then asserting bare is what made this flake under parallel load.
    // D2 is DROUGHT_CATEGORY_CODE[3] — once for the spread, once as the
    // final class.
    await waitFor(() => expect(screen.getAllByText("D2")).toHaveLength(2));
    // "Validated" is also a status-filter tab, so match the row's tag only.
    // The tab renders after /stats resolves, which is what made an ambiguous
    // getByText here look like a load flake rather than a bad query.
    const tags = screen
      .getAllByText("Validated")
      .filter((el) => el.tagName !== "BUTTON");
    expect(tags).toHaveLength(1);
  });

  it("shows no final D-class while a row is still awaiting", async () => {
    respond([{ ...ROW, status: "awaiting", validated_category: null }]);
    await renderPage();

    await waitFor(() => expect(urlsRequested()).toHaveLength(1));
    await waitFor(() => expect(screen.getAllByText("D2")).toHaveLength(1));
  });

  it("renders an em dash for a null consensus rather than 0%", async () => {
    respond([{ ...ROW, consensus: null }]);
    await renderPage();

    await waitFor(() => expect(screen.getByText("—")).toBeInTheDocument());
    expect(screen.queryByText("null%")).not.toBeInTheDocument();
  });

  it("sends ?agreement= straight through to the server", async () => {
    currentParams = new URLSearchParams("agreement=undisputed&status=ready");
    await renderPage();

    await waitFor(() => expect(urlsRequested()).toHaveLength(1));
    expect(urlsRequested()[0]).toContain("agreement=undisputed");
  });

  it("pins the Ready tab when Non-disputed only is switched on", async () => {
    // The bulk button's N is this table's count, so the filter the admin sees
    // has to be the set the server will write (D-3). Without status=ready the
    // count would include rows bulk refuses to touch.
    await renderPage();
    await waitFor(() => expect(urlsRequested()).toHaveLength(1));

    fireEvent.click(screen.getByRole("checkbox", { name: /non-disputed/i }));

    await waitFor(() => expect(replace).toHaveBeenCalled());
    const next = replace.mock.calls.at(-1)[0];
    expect(next).toContain("agreement=undisputed");
    expect(next).toContain("status=ready");
    expect(next).toContain("page=1");
  });

  it("clears the agreement filter when a status tab is picked", async () => {
    currentParams = new URLSearchParams("agreement=disagreement");
    await renderPage();
    await waitFor(() => expect(urlsRequested()).toHaveLength(1));

    fireEvent.click(screen.getByRole("button", { name: "Ready" }));

    await waitFor(() => expect(replace).toHaveBeenCalled());
    expect(replace.mock.calls.at(-1)[0]).not.toContain("agreement");
  });

  it("drills into the disagreement card", async () => {
    await renderPage();
    await waitFor(() => expect(urlsRequested()).toHaveLength(1));

    fireEvent.click(
      await screen.findByRole("button", { name: /High disagreement\s*:\s*3/ }),
    );

    await waitFor(() => expect(replace).toHaveBeenCalled());
    const next = replace.mock.calls.at(-1)[0];
    expect(next).toContain("agreement=disagreement");
    // Disagreement cross-cuts all three statuses, so pinning a tab here would
    // hide most of what the card counted.
    expect(next).not.toContain("status=");
  });

  it("clicking the disagreement card again clears the filter", async () => {
    // A one-way filter strands the admin on a subset of the queue with
    // nothing on screen saying why, and no way back except editing the URL.
    currentParams = new URLSearchParams("agreement=disagreement");
    await renderPage();

    const card = await screen.findByRole("button", {
      name: /High disagreement\s*:\s*3/,
    });
    expect(card).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(card);

    await waitFor(() => expect(replace).toHaveBeenCalled());
    expect(replace.mock.calls.at(-1)[0]).not.toContain("agreement");
  });

  it("shows the disagreement card as unpressed when its filter is off", async () => {
    await renderPage();

    const card = await screen.findByRole("button", {
      name: /High disagreement\s*:\s*3/,
    });
    expect(card).toHaveAttribute("aria-pressed", "false");
  });

  it("offers bulk validation only while the non-disputed filter is on", async () => {
    await renderPage();
    await waitFor(() => expect(urlsRequested()).toHaveLength(1));
    expect(
      screen.queryByRole("button", { name: /validate all/i }),
    ).not.toBeInTheDocument();

    currentParams = new URLSearchParams("agreement=undisputed&status=ready");
    cleanup();
    await renderPage();

    expect(
      await screen.findByRole("button", { name: /validate all 59/i }),
    ).toBeInTheDocument();
  });

  it("writes nothing until the confirmation is accepted", async () => {
    currentParams = new URLSearchParams("agreement=undisputed&status=ready");
    await renderPage();
    const before = api.mock.calls.length;

    fireEvent.click(
      await screen.findByRole("button", { name: /validate all 59/i }),
    );

    // The confirm dialog is open; no POST may have happened yet.
    await screen.findByText("Validate all non-disputed Tinkhundla?");
    expect(
      api.mock.calls.slice(before).filter(([method]) => method === "POST"),
    ).toHaveLength(0);
  });

  it("posts the active search so bulk writes only what is on screen", async () => {
    currentParams = new URLSearchParams(
      "agreement=undisputed&status=ready&search=kub",
    );
    await renderPage();

    fireEvent.click(
      await screen.findByRole("button", { name: /validate all 59/i }),
    );
    await screen.findByText("Validate all non-disputed Tinkhundla?");
    fireEvent.click(screen.getByRole("button", { name: "Validate all" }));

    await waitFor(() =>
      expect(
        api.mock.calls.filter(([method]) => method === "POST"),
      ).toHaveLength(1),
    );
    const [, url, body] = api.mock.calls.find(([m]) => m === "POST");
    expect(url).toBe("/admin/validation/4/bulk");
    expect(body).toEqual({ search: "kub" });
  });

  it("warns when a single working group is reviewing the publication", async () => {
    api.mockImplementation((_method, url) =>
      Promise.resolve(
        url.includes("/stats")
          ? { ...STATS, meta: { ...STATS.meta, reviewers_required: 1 } }
          : { data: [ROW], total: 59, current: 1 },
      ),
    );
    await renderPage();

    expect(
      await screen.findByText(/only one Technical Working Group/i),
    ).toBeInTheDocument();
  });

  it("does not warn when the panel spans two working groups", async () => {
    await renderPage();
    await waitFor(() => expect(urlsRequested()).toHaveLength(1));

    expect(
      screen.queryByText(/only one Technical Working Group/i),
    ).not.toBeInTheDocument();
  });

  it("surfaces a retry when the queue cannot be loaded", async () => {
    api.mockRejectedValue(new Error("boom"));
    render(<ValidationDetailPage />);

    await waitFor(() =>
      expect(
        screen.getByText("Could not load the validation queue."),
      ).toBeVisible(),
    );
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});
