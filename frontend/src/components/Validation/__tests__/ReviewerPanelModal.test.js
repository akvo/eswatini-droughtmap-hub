import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { api } from "@/lib";
import ReviewerPanelModal from "../ReviewerPanelModal";

jest.setTimeout(30000);

jest.mock("@/lib", () => ({ api: jest.fn() }));

beforeAll(() => {
  window.matchMedia = jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }));
});

/**
 * Only Select is stubbed. Its style injection emits
 * `:scope +.ant-select-item-option-selected...`, which jsdom's selector engine
 * rejects outright — a limitation of the test DOM, not of the component. The
 * stub renders the options it was handed, which is the part these tests are
 * actually about: which reviewers are offered.
 */
jest.mock("antd", () => {
  const actual = jest.requireActual("antd");
  const StubSelect = ({ options = [], value = [], onChange, placeholder }) => (
    <div data-testid="reviewer-select">
      <span>{placeholder}</span>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange?.([...value, o.value])}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
  return { ...actual, Select: StubSelect };
});

const PANEL = [
  {
    id: 7,
    name: "Ayanda Ropa",
    technical_working_group: "MET (Meteorological Office)",
    is_completed: true,
  },
  {
    id: 9,
    name: "Sipho Dlamini",
    technical_working_group: "DWA (Department of Water Affairs)",
    is_completed: false,
  },
];

const respond = (panel = PANEL) =>
  api.mockImplementation((method, url) => {
    if (method === "GET" && url.startsWith("/admin/publication/")) {
      return Promise.resolve({
        id: 4,
        year_month: "2026-05",
        reviewers: panel,
      });
    }
    if (method === "GET" && url.startsWith("/admin/reviewers")) {
      return Promise.resolve({
        data: [
          ...panel,
          { id: 11, name: "Thandi Nkosi", technical_working_group: "NDMA" },
        ],
      });
    }
    if (method === "POST") return Promise.resolve({ added: 1, reviewers: [] });
    return Promise.resolve({});
  });

beforeEach(() => {
  api.mockReset();
  respond();
});

const loaded = () => screen.findByText("Ayanda Ropa");

describe("ReviewerPanelModal", () => {
  it("offers Remove only for a reviewer who has not submitted", async () => {
    render(<ReviewerPanelModal open publicationId={4} />);
    await loaded();

    // One removable reviewer, one locked — not two of either.
    expect(screen.getAllByRole("button", { name: "Remove" })).toHaveLength(1);
    expect(screen.getByText("Locked")).toBeInTheDocument();
  });

  it("does not offer to add someone already on the panel", async () => {
    render(<ReviewerPanelModal open publicationId={4} />);
    await loaded();

    const choices = screen.getByTestId("reviewer-select");
    expect(choices).toHaveTextContent("Thandi Nkosi");
    // Ayanda is on the panel already; a duplicate Review would double-count
    // their working group toward coverage.
    expect(choices).not.toHaveTextContent("Ayanda Ropa");
  });

  const stage = (name) => {
    fireEvent.click(screen.getByRole("button", { name }));
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
  };

  const posts = () => api.mock.calls.filter(([m]) => m === "POST");

  it("queues a reviewer without writing or emailing anything", async () => {
    // An email cannot be recalled, so Add must be undoable. Writing on Add
    // meant the invitation was already gone by the time a mis-click was
    // noticed.
    render(<ReviewerPanelModal open publicationId={4} />);
    await loaded();

    stage(/Thandi Nkosi/);

    expect(await screen.findByText("Not invited")).toBeInTheDocument();
    expect(posts()).toHaveLength(0);
  });

  it("never invites someone who was queued and then removed", async () => {
    render(<ReviewerPanelModal open publicationId={4} />);
    await loaded();

    stage(/Thandi Nkosi/);
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));

    // Nothing queued, so there is nothing to send.
    expect(
      screen.getByRole("button", { name: /send invitations/i }),
    ).toBeDisabled();
    expect(posts()).toHaveLength(0);
  });

  it("sends the invitation text, so the reviewer is actually told", async () => {
    // The server skips the email when subject/message are absent. Posting
    // only the ids assigns someone work they never hear about — and nothing
    // in the UI would look wrong (AC-5.1).
    render(<ReviewerPanelModal open publicationId={4} />);
    await loaded();

    stage(/Thandi Nkosi/);
    fireEvent.click(screen.getByRole("button", { name: /send 1 invitation/i }));

    await waitFor(() => expect(posts()).toHaveLength(1));
    const [, , body] = posts()[0];
    expect(body.reviewers).toEqual([11]);
    expect(body.subject).toContain("2026-05");
    expect(body.message).toContain("{{reviewer_name}}");
  });

  it("surfaces a refusal instead of reporting success", async () => {
    // api() resolves on 4xx, so a rejected delete arrives as a value. Treated
    // as success it would look like the reviewer had gone.
    api.mockImplementation((method, url) => {
      if (method === "DELETE") {
        return Promise.resolve({
          reviewers: [
            "Sipho Dlamini has already submitted a review and cannot be " +
              "removed.",
          ],
        });
      }
      if (method === "GET" && url.startsWith("/admin/publication/")) {
        return Promise.resolve({ id: 4, reviewers: PANEL });
      }
      return Promise.resolve({ data: PANEL });
    });
    render(<ReviewerPanelModal open publicationId={4} />);
    await loaded();

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    expect(
      await screen.findByText(/has already submitted a review/),
    ).toBeVisible();
    expect(screen.getByText("Sipho Dlamini")).toBeInTheDocument();
  });

  it("tells the caller when the panel changed", async () => {
    const onChanged = jest.fn();
    api.mockImplementation((method, url) => {
      if (method === "DELETE") return Promise.resolve(null);
      if (method === "GET" && url.startsWith("/admin/publication/")) {
        return Promise.resolve({ id: 4, reviewers: PANEL });
      }
      return Promise.resolve({ data: PANEL });
    });
    render(<ReviewerPanelModal open publicationId={4} onChanged={onChanged} />);
    await loaded();

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    // reviewers_required moves with the panel, which moves rows between
    // Ready and Awaiting — the queue behind this modal is now stale.
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });
});
