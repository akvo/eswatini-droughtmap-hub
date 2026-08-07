import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { api } from "@/lib";
import ValidationDecisionPage, { composeDefaultReasoning } from "../page";

jest.setTimeout(30000);

jest.mock("@/lib", () => ({ api: jest.fn() }));

jest.mock("@/components", () => ({
  Can: ({ children }) => <>{children}</>,
  FeedbackSection: () => null,
}));

const push = jest.fn();
let currentParams = new URLSearchParams();

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "4", administrationId: "12" }),
  useRouter: () => ({ push }),
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

const REVIEW = (over = {}) => ({
  user_id: 7,
  initials: "AR",
  name: "Ayanda Ropa",
  organisation: 3,
  email: "ayanda@example.org",
  submitted_at: "2026-05-09T10:12:00Z",
  category: 3,
  comment: "2 of 3 sources support D2.",
  hidden: false,
  ...over,
});

const PAYLOAD = (over = {}) => ({
  meta: {
    publication_id: 4,
    year_month: "2026-05",
    reviewers_required: 5,
    can_submit: true,
    viewer: { name: "Nomsa Dube", organisation: 1 },
    prev_administration_id: 11,
    next_administration_id: 19,
    queue_page: 2,
    ...(over.meta || {}),
  },
  administration_id: 12,
  label: "Kubuta",
  region: "Shiselweni",
  zone: "middleveld",
  status: "ready",
  awaiting_count: 0,
  reviews_completed: 4,
  reviews_total: 5,
  consensus: 80,
  majority_category: 3,
  validated_category: null,
  confidence: 2,
  confidence_band: "low",
  is_override: false,
  masked: false,
  agreement:
    "agreement" in over
      ? over.agreement
      : {
          band: "high",
          majority_count: 3,
          total_submitted: 4,
          is_tie: false,
          tied_categories: [],
          distribution: [
            { category: 1, count: 1 },
            { category: 3, count: 3 },
          ],
        },
  reviews: over.reviews || [REVIEW()],
  decision: over.decision ?? null,
  ...Object.fromEntries(
    Object.entries(over).filter(
      ([k]) => !["meta", "agreement", "reviews", "decision"].includes(k),
    ),
  ),
});

const respond = (payload, history = []) =>
  api.mockImplementation((method, url) => {
    if (method === "PUT") return Promise.resolve({ is_draft: false });
    if (url.endsWith("/history")) return Promise.resolve({ data: history });
    return Promise.resolve(payload);
  });

const reasoningBox = () => screen.getByPlaceholderText("Add reviewer notes...");

/** The textarea renders before the fetch resolves, so it is no proof of
 *  load. Wait for something that only exists once the payload arrives. */
const loaded = () => screen.findByRole("heading", { name: "Kubuta" });

beforeEach(() => {
  currentParams = new URLSearchParams();
  push.mockClear();
  respond(PAYLOAD());
});

describe("composeDefaultReasoning", () => {
  it("names the count and the short code", () => {
    expect(
      composeDefaultReasoning(
        { majority_count: 3, total_submitted: 4, is_tie: false },
        3,
      ),
    ).toBe("Accepting the reviewer majority (3 of 4 chose D2).");
  });

  it("is empty on a tie — there is no majority to claim", () => {
    expect(
      composeDefaultReasoning(
        { majority_count: 2, total_submitted: 4, is_tie: true },
        3,
      ),
    ).toBe("");
  });

  it("is empty when nothing has been submitted", () => {
    expect(
      composeDefaultReasoning({ majority_count: 0, total_submitted: 0 }, null),
    ).toBe("");
  });
});

describe("Validation decision page", () => {
  it("pre-selects the majority and pre-fills the reasoning", async () => {
    render(<ValidationDecisionPage />);
    await waitFor(() =>
      expect(reasoningBox()).toHaveValue(
        "Accepting the reviewer majority (3 of 4 chose D2).",
      ),
    );
  });

  it("re-opens a saved draft with its own selection and text", async () => {
    // Without this the draft would re-open showing the majority chip and an
    // empty textarea, looking like it had never been saved (AC-6.5).
    respond(
      PAYLOAD({
        decision: {
          category: 5,
          reasoning: "Waiting on the Met station re-check.",
          is_draft: true,
          updated_at: "2026-05-18T08:31:00Z",
        },
      }),
    );
    render(<ValidationDecisionPage />);

    await waitFor(() =>
      expect(reasoningBox()).toHaveValue(
        "Waiting on the Met station re-check.",
      ),
    );
  });

  it("renders the agreement bar from the server tally", async () => {
    render(<ValidationDecisionPage />);
    await waitFor(() =>
      expect(screen.getByText("3/4 reviewers chose")).toBeInTheDocument(),
    );
  });

  it("names the tie instead of claiming a majority", async () => {
    // The old client-side reduce kept the FIRST of two tied classes, so a
    // 2-2 tie printed "chose D1" while the chip pre-selected D2.
    respond(
      PAYLOAD({
        majority_category: 3,
        agreement: {
          band: "high",
          majority_count: 2,
          total_submitted: 4,
          is_tie: true,
          tied_categories: [2, 3],
          distribution: [
            { category: 2, count: 2 },
            { category: 3, count: 3 },
          ],
        },
      }),
    );
    render(<ValidationDecisionPage />);

    await waitFor(() =>
      expect(screen.getByText(/No single majority/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/D1 and D2/)).toBeInTheDocument();
    expect(screen.queryByText(/reviewers chose/)).not.toBeInTheDocument();
  });

  it("requires reasoning on a tie even when the chip is unchanged", async () => {
    respond(
      PAYLOAD({
        decision: {
          category: 3,
          reasoning: "",
          is_draft: true,
          updated_at: null,
        },
        agreement: {
          band: "high",
          majority_count: 2,
          total_submitted: 4,
          is_tie: true,
          tied_categories: [2, 3],
          distribution: [{ category: 3, count: 2 }],
        },
      }),
    );
    render(<ValidationDecisionPage />);

    await waitFor(() =>
      expect(
        screen.getByText("(required — the reviewers are tied)"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("button", { name: /submit decision/i }),
    ).toBeDisabled();
  });

  it("stays on the page when a submit is rejected", async () => {
    // api() resolves on 4xx, so a rejected write is a value. Treating it as
    // success would navigate the admin away believing the class was saved.
    api.mockImplementation((method, url) => {
      if (method === "PUT") {
        return Promise.resolve({
          reasoning: [
            "Reasoning is required when overriding the reviewer majority.",
          ],
        });
      }
      if (url.endsWith("/history")) return Promise.resolve({ data: [] });
      return Promise.resolve(PAYLOAD());
    });
    render(<ValidationDecisionPage />);
    await loaded();

    fireEvent.click(screen.getByRole("button", { name: /submit decision/i }));

    await waitFor(() =>
      expect(
        screen.getByText(
          "Reasoning is required when overriding the reviewer majority.",
        ),
      ).toBeVisible(),
    );
    expect(push).not.toHaveBeenCalled();
  });

  it("returns to the queue page the server reports, keeping filters", async () => {
    currentParams = new URLSearchParams("status=ready&search=kub");
    render(<ValidationDecisionPage />);
    await loaded();

    fireEvent.click(screen.getByRole("button", { name: /submit decision/i }));

    await waitFor(() => expect(push).toHaveBeenCalled());
    const target = push.mock.calls.at(-1)[0];
    expect(target).toContain("/validations/4?");
    expect(target).toContain("status=ready");
    expect(target).toContain("search=kub");
    expect(target).toContain("page=2"); // meta.queue_page, not the URL
  });

  it("carries the agreement filter through navigation", async () => {
    // Without this, Previous/Next walk the unfiltered queue and land the
    // admin on rows the filter had just excluded (AC-3.1).
    currentParams = new URLSearchParams("agreement=undisputed&status=ready");
    render(<ValidationDecisionPage />);
    await loaded();

    expect(
      api.mock.calls.find(
        ([m, url]) => m === "GET" && !url.endsWith("/history"),
      )[1],
    ).toContain("agreement=undisputed");

    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(push.mock.calls.at(-1)[0]).toContain("agreement=undisputed");
  });

  it("walks Previous/Next by the ids the server supplies", async () => {
    currentParams = new URLSearchParams("status=ready");
    render(<ValidationDecisionPage />);
    await loaded();

    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(push).toHaveBeenCalledWith("/validations/4/19?status=ready");

    fireEvent.click(screen.getByRole("button", { name: "Previous" }));
    expect(push).toHaveBeenCalledWith("/validations/4/11?status=ready");
  });

  it("disables Next at the end of the queue", async () => {
    respond(PAYLOAD({ meta: { next_administration_id: null } }));
    render(<ValidationDecisionPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Next" })).toBeDisabled(),
    );
  });

  it("masks colleagues and explains why", async () => {
    respond(
      PAYLOAD({
        masked: true,
        consensus: null,
        majority_category: null,
        agreement: null,
        reviews: [
          REVIEW(),
          REVIEW({
            user_id: null,
            initials: null,
            name: null,
            email: null,
            category: null,
            comment: null,
            submitted_at: null,
            hidden: true,
          }),
        ],
      }),
    );
    render(<ValidationDecisionPage />);
    await loaded();

    expect(
      screen.getByText(/Submit your own review for this Inkhundla/),
    ).toBeInTheDocument();
    expect(screen.queryByText("3/4 reviewers chose")).not.toBeInTheDocument();
  });

  it("shows the lock notice and no submit controls for a viewer", async () => {
    respond(
      PAYLOAD({
        meta: {
          can_submit: false,
          viewer: { name: "Sipho Dlamini", organisation: 5 },
        },
      }),
    );
    render(<ValidationDecisionPage />);
    // The notice renders before the fetch too (with an empty name), so the
    // load gate has to come first or this asserts nothing.
    await loaded();

    const notice = screen.getByText(/Only NDRMA can publish/);
    expect(notice.textContent).toContain("Sipho Dlamini");
    // organisation 5 is labelled through TWG_OPTIONS, not sent as a string.
    expect(notice.textContent).toContain("UNESWA");
    expect(
      screen.queryByRole("button", { name: /submit decision/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /save changes as draft/i }),
    ).not.toBeInTheDocument();
  });

  it("shows neither the lock notice nor the buttons while loading", async () => {
    // can_submit is false until the payload lands, so rendering the action
    // area early flashes "Only NDRMA can publish" at an admin.
    render(<ValidationDecisionPage />);
    expect(
      screen.queryByText(/Only NDRMA can publish/),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /submit decision/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/Loading decision/)).toBeInTheDocument();

    await loaded();
    expect(
      screen.getByRole("button", { name: /submit decision/i }),
    ).toBeInTheDocument();
  });

  it("labels the consensus band from the server, not a local threshold", async () => {
    render(<ValidationDecisionPage />);
    await loaded();
    expect(screen.getByText("High consensus")).toBeInTheDocument();
  });

  it("shows no band label when nothing has been submitted", async () => {
    respond(PAYLOAD({ consensus: null, agreement: null }));
    render(<ValidationDecisionPage />);
    await loaded();
    expect(screen.queryByText(/consensus$/i)).not.toBeInTheDocument();
  });

  it("renders the period as the full calendar month span", async () => {
    render(<ValidationDecisionPage />);
    await waitFor(() =>
      expect(screen.getByText("1 May 2026 - 31 May 2026")).toBeInTheDocument(),
    );
  });

  it("shows an em dash for a null consensus", async () => {
    respond(PAYLOAD({ consensus: null }));
    render(<ValidationDecisionPage />);
    await waitFor(() => expect(screen.getByText("—")).toBeInTheDocument());
  });
});
