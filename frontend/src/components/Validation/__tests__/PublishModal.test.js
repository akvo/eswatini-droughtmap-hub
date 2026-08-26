import React from "react";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import PublishModal, { overviewTitle } from "../PublishModal";
import { api } from "@/lib/api";

jest.setTimeout(30000);

jest.mock("@/lib/api", () => ({ api: jest.fn() }));

// Mirrors GET /insights/response-activities — the endpoint that also renders
// the National Overview cards, so the modal cannot show a different list.
const SECTORS = [
  {
    id: 3,
    key: "wash",
    label: "Water & Sanitation",
    activities: 2,
    tinkhundla: 27,
  },
  {
    id: 1,
    key: "food",
    label: "Food & Agriculture",
    activities: 2,
    tinkhundla: 31,
  },
];

beforeEach(() => {
  api.mockReset();
  api.mockResolvedValue({ sectors: SECTORS });
});

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

const type = (value) =>
  fireEvent.change(screen.getByPlaceholderText("Shown underneath the title"), {
    target: { value },
  });

const bulletinInput = () => screen.getByLabelText(/bulletin url/i);

const typeBulletin = (value) =>
  fireEvent.change(bulletinInput(), { target: { value } });

const publish = () =>
  fireEvent.click(screen.getByRole("button", { name: /^publish$/i }));

const sectorHeader = (label) =>
  screen.getByRole("button", { name: new RegExp(label) });

/** A row renders its textarea only while expanded, so a sector must be opened
 *  to be typed into — the same thing an admin does. Idempotent: one row is
 *  expanded by default, and clicking that one would collapse it. */
const openSector = (label) => {
  const header = sectorHeader(label);
  if (header.getAttribute("aria-expanded") !== "true") {
    fireEvent.click(header);
  }
};

// `selector` matters: antd labels the tab PANEL with the same text via
// aria-labelledby, so an unscoped query matches the panel as well.
const sectorBox = (label) =>
  screen.getByLabelText(new RegExp(label), { selector: "textarea" });

const typeSector = (label, value) =>
  fireEvent.change(sectorBox(label), { target: { value } });

/** Wait for the fetched tabs, then fill every sector. */
const fillSectors = async () => {
  await waitFor(() =>
    expect(sectorHeader("Water & Sanitation")).toBeInTheDocument(),
  );
  for (const s of SECTORS) {
    openSector(s.label);
    // eslint-disable-next-line no-await-in-loop
    await waitFor(() => expect(sectorBox(s.label)).toBeInTheDocument());
    typeSector(s.label, `${s.label} copy.`);
  }
};

const SECTOR_CONTEXT = {
  3: "Water & Sanitation copy.",
  1: "Food & Agriculture copy.",
};

describe("PublishModal", () => {
  it("generates the title from the publication month, read-only", () => {
    render(<PublishModal open yearMonth="2026-05" onPublish={jest.fn()} />);
    expect(screen.getByText(overviewTitle("2026-05"))).toBeInTheDocument();
    // The title is generated (D-4) — there must be no input for it.
    expect(
      screen.queryByPlaceholderText(/hero headline/i),
    ).not.toBeInTheDocument();
  });

  it("renders one collapsible row per sector the API returns", async () => {
    render(<PublishModal open yearMonth="2026-05" onPublish={jest.fn()} />);

    await waitFor(() =>
      expect(sectorHeader("Water & Sanitation")).toBeInTheDocument(),
    );
    SECTORS.forEach((s) => expect(sectorHeader(s.label)).toBeInTheDocument());
    // The old hardcoded list named sectors that were never fetched.
    expect(
      screen.queryByRole("button", { name: /Health & Nutrition/ }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Auto-generated")).not.toBeInTheDocument();
    // Counts stay derived — shown beside the box, not typed (D-1).
    expect(
      screen.getByText(/2 activities · 27 Tinkhundla/),
    ).toBeInTheDocument();
  });

  it("seeds EVERY sector box, not just the first", async () => {
    // The whole map has to arrive: the modal submits all of it on every
    // update, so a sector it cannot prefill is one the admin must retype.
    const { rerender } = render(
      <PublishModal open={false} yearMonth="2026-05" onPublish={jest.fn()} />,
    );
    rerender(
      <PublishModal
        open
        yearMonth="2026-05"
        currentNarrative="Hello"
        currentSectorContext={{ 3: "WASH copy.", 1: "Food copy." }}
        published
        onPublish={jest.fn()}
      />,
    );

    await waitFor(() =>
      expect(sectorHeader("Water & Sanitation")).toBeInTheDocument(),
    );
    openSector("Water & Sanitation");
    await waitFor(() =>
      expect(sectorBox("Water & Sanitation")).toHaveValue("WASH copy."),
    );
    openSector("Food & Agriculture");
    await waitFor(() =>
      expect(sectorBox("Food & Agriculture")).toHaveValue("Food copy."),
    );
    // Both already written, so neither dot is red and publish is unblocked.
    expect(screen.queryByText(/Sector information is required/)).toBeNull();
  });

  it("marks a sector with nothing triggered as optional", async () => {
    api.mockResolvedValue({
      sectors: [SECTORS[0], { ...SECTORS[1], tinkhundla: 0 }],
    });
    const onPublish = jest.fn().mockResolvedValue(null);
    render(<PublishModal open yearMonth="2026-05" onPublish={onPublish} />);

    await waitFor(() =>
      expect(sectorHeader("Water & Sanitation")).toBeInTheDocument(),
    );
    // Scoped to the header: the Bulletin URL label also reads "(optional)",
    // and so does the legend.
    expect(
      within(sectorHeader("Food & Agriculture")).getByText("(optional)"),
    ).toBeInTheDocument();

    // Only the triggered sector is required, so this submits with one blank.
    // WASH is required-and-empty, so the accordion opens it by default.
    await waitFor(() =>
      expect(sectorBox("Water & Sanitation")).toBeInTheDocument(),
    );
    typeSector("Water & Sanitation", "Boreholes restored.");
    type("Conditions eased.");
    publish();

    await waitFor(() => expect(onPublish).toHaveBeenCalledTimes(1));
    expect(onPublish.mock.calls[0][0].sectorContext).toEqual({
      3: "Boreholes restored.",
    });
  });

  it("requires every sector box before it will submit", async () => {
    const onPublish = jest.fn().mockResolvedValue(null);
    render(<PublishModal open yearMonth="2026-05" onPublish={onPublish} />);

    await waitFor(() =>
      expect(sectorBox("Water & Sanitation")).toBeInTheDocument(),
    );
    type("Conditions eased.");
    typeSector("Water & Sanitation", "Boreholes restored.");
    publish();

    await waitFor(() =>
      expect(
        screen.getByText(/Sector information is required for/),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByText(/Food & Agriculture/, { selector: ".ant-alert *" }),
    ).toBeInTheDocument();
    expect(onPublish).not.toHaveBeenCalled();
  });

  it("seeds the sector boxes from an already-published map", async () => {
    const { rerender } = render(
      <PublishModal open={false} yearMonth="2026-05" onPublish={jest.fn()} />,
    );
    rerender(
      <PublishModal
        open
        yearMonth="2026-05"
        currentNarrative="Hello"
        currentSectorContext={{ 3: "Existing WASH copy." }}
        published
        onPublish={jest.fn()}
      />,
    );

    // WASH already has copy, so the first sector still needing some is the
    // one that opens — open WASH to read what was seeded into it.
    await waitFor(() =>
      expect(sectorHeader("Water & Sanitation")).toBeInTheDocument(),
    );
    openSector("Water & Sanitation");
    await waitFor(() =>
      expect(sectorBox("Water & Sanitation")).toHaveValue(
        "Existing WASH copy.",
      ),
    );
  });

  it("submits the description and the bulletin URL", async () => {
    const onPublish = jest.fn().mockResolvedValue(null);
    render(<PublishModal open yearMonth="2026-05" onPublish={onPublish} />);

    await fillSectors();
    type("Conditions eased across the Lowveld.");
    typeBulletin("  https://ndma.org.sz/bulletin-2026-05.pdf  ");
    publish();

    await waitFor(() => expect(onPublish).toHaveBeenCalledTimes(1));
    expect(onPublish).toHaveBeenCalledWith({
      narrative: "Conditions eased across the Lowveld.",
      bulletinUrl: "https://ndma.org.sz/bulletin-2026-05.pdf",
      sectorContext: SECTOR_CONTEXT,
    });
  });

  it("publishes without a bulletin URL — it is optional", async () => {
    const onPublish = jest.fn().mockResolvedValue(null);
    render(<PublishModal open yearMonth="2026-05" onPublish={onPublish} />);

    await fillSectors();
    type("No bulletin this month.");
    publish();

    await waitFor(() => expect(onPublish).toHaveBeenCalledTimes(1));
    expect(onPublish).toHaveBeenCalledWith({
      narrative: "No bulletin this month.",
      bulletinUrl: "",
      sectorContext: SECTOR_CONTEXT,
    });
  });

  it("sends an emptied bulletin URL so clearing one actually clears it", async () => {
    const onPublish = jest.fn().mockResolvedValue(null);
    const { rerender } = render(
      <PublishModal open={false} yearMonth="2026-05" onPublish={onPublish} />,
    );
    rerender(
      <PublishModal
        open
        yearMonth="2026-05"
        currentNarrative="Hello world"
        currentBulletinUrl="https://ndma.org.sz/old.pdf"
        currentSectorContext={SECTOR_CONTEXT}
        published
        onPublish={onPublish}
      />,
    );

    await waitFor(() =>
      expect(sectorHeader("Water & Sanitation")).toBeInTheDocument(),
    );
    typeBulletin("");
    fireEvent.click(screen.getByRole("button", { name: /^update$/i }));

    await waitFor(() => expect(onPublish).toHaveBeenCalledTimes(1));
    expect(onPublish).toHaveBeenCalledWith({
      narrative: "Hello world",
      bulletinUrl: "",
      sectorContext: SECTOR_CONTEXT,
    });
  });

  it("seeds the description and bulletin URL from the published map, and says Update", () => {
    // `meta` arrives after the first render, so seeding only in useState
    // leaves an already-published map editing an empty box (bug: #317).
    // The modal submits both fields on every update, so a field it fails to
    // seed is a field it silently wipes.
    const { rerender } = render(
      <PublishModal open={false} yearMonth="2026-05" onPublish={jest.fn()} />,
    );
    rerender(
      <PublishModal
        open
        yearMonth="2026-05"
        currentNarrative="Hello world"
        currentBulletinUrl="https://ndma.org.sz/bulletin-2026-05.pdf"
        published
        onPublish={jest.fn()}
      />,
    );

    expect(
      screen.getByPlaceholderText("Shown underneath the title"),
    ).toHaveValue("Hello world");
    expect(bulletinInput()).toHaveValue(
      "https://ndma.org.sz/bulletin-2026-05.pdf",
    );
    expect(
      screen.getByRole("button", { name: /^update$/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^publish$/i }),
    ).not.toBeInTheDocument();
  });

  it("requires a description before it will submit", async () => {
    const onPublish = jest.fn().mockResolvedValue(null);
    render(<PublishModal open yearMonth="2026-05" onPublish={onPublish} />);

    type("   ");
    publish();

    await waitFor(() =>
      expect(
        screen.getByText("A description is required."),
      ).toBeInTheDocument(),
    );
    expect(onPublish).not.toHaveBeenCalled();
  });

  it("caps the description at the configured character count and shows it", () => {
    render(
      <PublishModal
        open
        yearMonth="2026-05"
        maxChars={10}
        onPublish={jest.fn()}
      />,
    );

    type("Dry east");
    expect(
      screen.getByPlaceholderText("Shown underneath the title"),
    ).toHaveAttribute("maxlength", "10");
    expect(screen.getByText("8 / 10")).toBeInTheDocument();
  });

  it("refuses an over-long description seeded from a published map", async () => {
    // maxLength only governs typing. A narrative that arrives too long — from
    // a map published before the ceiling existed — would otherwise sail
    // through untouched.
    const onPublish = jest.fn().mockResolvedValue(null);
    const { rerender } = render(
      <PublishModal open={false} yearMonth="2026-05" onPublish={onPublish} />,
    );
    rerender(
      <PublishModal
        open
        yearMonth="2026-05"
        maxChars={10}
        currentNarrative="Dry across the east"
        published
        onPublish={onPublish}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /^update$/i }));

    await waitFor(() =>
      expect(
        screen.getByText("The description must be 10 characters or fewer."),
      ).toBeInTheDocument(),
    );
    expect(onPublish).not.toHaveBeenCalled();
  });

  it("stays open and keeps the typed description when publish is rejected", async () => {
    // The API helper RESOLVES on 4xx rather than rejecting, so a rejected
    // publish arrives as a value. If this were handled with try/catch the
    // rejection would look identical to success and the admin would be
    // navigated away believing the map went out.
    const onPublish = jest
      .fn()
      .mockResolvedValue(
        "Cannot publish: 12 of 59 Tinkhundla are not validated yet.",
      );
    const onCancel = jest.fn();
    render(
      <PublishModal
        open
        yearMonth="2026-05"
        onCancel={onCancel}
        onPublish={onPublish}
      />,
    );

    type("Drought persists in the east.");
    publish();

    await waitFor(() =>
      expect(
        screen.getByText(
          "Cannot publish: 12 of 59 Tinkhundla are not validated yet.",
        ),
      ).toBeInTheDocument(),
    );
    // Four paragraphs of typing must survive a race with a colleague.
    expect(
      screen.getByPlaceholderText("Shown underneath the title"),
    ).toHaveValue("Drought persists in the east.");
    expect(onCancel).not.toHaveBeenCalled();
  });
});
