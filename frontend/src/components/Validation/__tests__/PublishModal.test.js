import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import PublishModal, { overviewTitle } from "../PublishModal";

jest.setTimeout(30000);

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

describe("PublishModal", () => {
  it("generates the title from the publication month, read-only", () => {
    render(<PublishModal open yearMonth="2026-05" onPublish={jest.fn()} />);
    expect(screen.getByText(overviewTitle("2026-05"))).toBeInTheDocument();
    // The title is generated (D-4) — there must be no input for it.
    expect(
      screen.queryByPlaceholderText(/hero headline/i),
    ).not.toBeInTheDocument();
  });

  it("shows the four sector cards as auto-generated, not editable", () => {
    render(<PublishModal open yearMonth="2026-05" onPublish={jest.fn()} />);
    [
      "Water & Sanitation",
      "Food & Agriculture",
      "Health & Nutrition",
      "Environment & Energy",
    ].forEach((label) => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
    expect(screen.getAllByText("Auto-generated")).toHaveLength(4);
  });

  it("submits the description and the bulletin URL", async () => {
    const onPublish = jest.fn().mockResolvedValue(null);
    render(<PublishModal open yearMonth="2026-05" onPublish={onPublish} />);

    type("Conditions eased across the Lowveld.");
    typeBulletin("  https://ndma.org.sz/bulletin-2026-05.pdf  ");
    publish();

    await waitFor(() => expect(onPublish).toHaveBeenCalledTimes(1));
    expect(onPublish).toHaveBeenCalledWith({
      narrative: "Conditions eased across the Lowveld.",
      bulletinUrl: "https://ndma.org.sz/bulletin-2026-05.pdf",
    });
  });

  it("publishes without a bulletin URL — it is optional", async () => {
    const onPublish = jest.fn().mockResolvedValue(null);
    render(<PublishModal open yearMonth="2026-05" onPublish={onPublish} />);

    type("No bulletin this month.");
    publish();

    await waitFor(() => expect(onPublish).toHaveBeenCalledTimes(1));
    expect(onPublish).toHaveBeenCalledWith({
      narrative: "No bulletin this month.",
      bulletinUrl: "",
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
        published
        onPublish={onPublish}
      />,
    );

    typeBulletin("");
    fireEvent.click(screen.getByRole("button", { name: /^update$/i }));

    await waitFor(() => expect(onPublish).toHaveBeenCalledTimes(1));
    expect(onPublish).toHaveBeenCalledWith({
      narrative: "Hello world",
      bulletinUrl: "",
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
