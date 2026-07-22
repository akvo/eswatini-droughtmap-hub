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

  it("submits only the description", async () => {
    const onPublish = jest.fn().mockResolvedValue(null);
    render(<PublishModal open yearMonth="2026-05" onPublish={onPublish} />);

    type("Conditions eased across the Lowveld.");
    publish();

    await waitFor(() => expect(onPublish).toHaveBeenCalledTimes(1));
    expect(onPublish).toHaveBeenCalledWith({
      narrative: "Conditions eased across the Lowveld.",
    });
  });

  it("requires a description before it will submit", async () => {
    const onPublish = jest.fn().mockResolvedValue(null);
    render(<PublishModal open yearMonth="2026-05" onPublish={onPublish} />);

    type("   ");
    publish();

    await waitFor(() =>
      expect(screen.getByText("A description is required.")).toBeVisible(),
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
      ).toBeVisible(),
    );
    // Four paragraphs of typing must survive a race with a colleague.
    expect(
      screen.getByPlaceholderText("Shown underneath the title"),
    ).toHaveValue("Drought persists in the east.");
    expect(onCancel).not.toHaveBeenCalled();
  });
});
