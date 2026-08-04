import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  within,
} from "@testing-library/react";
import { Modal } from "antd";
import ActivityDetailSlideIn from "../ActivityDetailSlideIn";
import { api } from "@/lib/api";
import { ACTIVITY_STATUS, USER_ROLES } from "@/static/config";

jest.setTimeout(30000);

// Mock the api function
jest.mock("@/lib/api", () => ({
  api: jest.fn(),
  getSourceFileBase64: jest.fn(),
}));

jest.mock("@/context/UserContextProvider", () => ({
  useUserContext: () => ({
    role: "admin",
    abilities: [
      { action: "update", subject: "Activity" },
      { action: "create", subject: "Activity" },
    ],
  }),
}));

const mockActivity = {
  id: 12,
  code: "ACT-WASH-12",
  title: "Emergency Water Trucking",
  description: "Provide emergency water deliveries.",
  sector: 3,
  sector_label: "Water & Sanitation",
  status: ACTIVITY_STATUS.draft,
  owner: "Ministry of Water",
  coord_with: "NDRMA",
  response_type: 2,
  response_type_label: "Institutional",
  source_doc: "National Response Plan 2026",
  source_file: "uploads/plan.pdf",
  version: "v1.2",
  updated_at: "2026-06-15T10:00:00Z",
  activated_by_name: "John Doe",
  activated_at: "2026-06-16T12:00:00Z",
  notes: "High priority wash activity.",
  triggers: {
    dclass: { class: 3, months: 2 },
    vuln: { op: 1, value: 3 },
    exp: [{ indicator: "water", op: 1, value: 5000 }],
    other: "Dry forecast",
  },
};

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

describe("ActivityDetailSlideIn Component", () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Set up robust, order-independent mock implementations
    api.mockImplementation((method, url) => {
      if (method === "GET" && url === "/activity/12") {
        return Promise.resolve(mockActivity);
      }
      if (method === "POST" && url === "/activities/trigger-preview") {
        return Promise.resolve({ matched: 12, total: 59 });
      }
      if (method === "POST" && url === "/activity/12/transition") {
        return Promise.resolve({ success: true });
      }
      return Promise.reject(new Error(`Unhandled mock call: ${method} ${url}`));
    });
  });

  afterEach(() => {
    // Clean up any remaining Antd modals/portals cleanly via Antd API
    Modal.destroyAll();
  });

  it("fetches and renders activity details correctly", async () => {
    render(
      <ActivityDetailSlideIn
        activityId={12}
        onClose={jest.fn()}
        onEdit={jest.fn()}
        onRefresh={jest.fn()}
      />,
    );

    // Wait for the detail fetch to complete
    await waitFor(() => {
      expect(screen.getByText("Emergency Water Trucking")).toBeInTheDocument();
    });

    expect(screen.getByText("ACT-WASH-12")).toBeInTheDocument();
    expect(screen.getByText("Water & Sanitation")).toBeInTheDocument();
    expect(screen.getByText("Ministry of Water")).toBeInTheDocument();
    expect(screen.getByText("NDRMA")).toBeInTheDocument();
    expect(screen.getByText("Institutional")).toBeInTheDocument();
    expect(screen.getByText("National Response Plan 2026")).toBeInTheDocument();
    expect(screen.getByText(/Download source file/)).toBeInTheDocument();
    expect(screen.getByText("v1.2")).toBeInTheDocument();
    expect(screen.getByText("15/06/2026")).toBeInTheDocument(); // updated_at date format
    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("16/06/2026")).toBeInTheDocument(); // activated_at date format
    expect(
      screen.getByText(/High priority wash activity\./),
    ).toBeInTheDocument();
  });

  it("calls onClose when escape key is pressed", async () => {
    const handleClose = jest.fn();
    render(
      <ActivityDetailSlideIn
        activityId={12}
        onClose={handleClose}
        onEdit={jest.fn()}
        onRefresh={jest.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Emergency Water Trucking")).toBeInTheDocument();
    });

    fireEvent.keyDown(window, { key: "Escape", code: "Escape" });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("handles Set active transition correctly", async () => {
    const handleRefresh = jest.fn();
    const handleClose = jest.fn();
    render(
      <ActivityDetailSlideIn
        activityId={12}
        onClose={handleClose}
        onEdit={jest.fn()}
        onRefresh={handleRefresh}
      />,
    );

    await waitFor(() => {
      const footer = document.querySelector(".sticky.bottom-0");
      expect(within(footer).getByText("Set active")).toBeInTheDocument();
    });

    const footer = document.querySelector(".sticky.bottom-0");
    fireEvent.click(within(footer).getByText("Set active"));

    // Antd Modal confirmation click (use selector to avoid text ambiguity with portal nodes)
    await waitFor(() => {
      const confirmBtn = document.querySelector(
        ".ant-modal-confirm-btns button:last-child",
      );
      expect(confirmBtn).toBeInTheDocument();
    });
    const confirmBtn = document.querySelector(
      ".ant-modal-confirm-btns button:last-child",
    );
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api).toHaveBeenCalledWith("POST", "/activity/12/transition", {
        to_status: ACTIVITY_STATUS.active,
      });
    });

    // Wait for the async ok handler to fully finish and close the modal/slide-in
    await waitFor(() => {
      expect(handleRefresh).toHaveBeenCalled();
      expect(handleClose).toHaveBeenCalled();
    });
  });

  it("handles Archive transition correctly", async () => {
    const handleRefresh = jest.fn();
    const handleClose = jest.fn();
    render(
      <ActivityDetailSlideIn
        activityId={12}
        onClose={handleClose}
        onEdit={jest.fn()}
        onRefresh={handleRefresh}
      />,
    );

    await waitFor(() => {
      const footer = document.querySelector(".sticky.bottom-0");
      expect(within(footer).getByText("Archive")).toBeInTheDocument();
    });

    const footer = document.querySelector(".sticky.bottom-0");
    fireEvent.click(within(footer).getByText("Archive"));

    // Antd Modal confirmation click (use selector to avoid text ambiguity with portal nodes)
    await waitFor(() => {
      const confirmBtn = document.querySelector(
        ".ant-modal-confirm-btns button:last-child",
      );
      expect(confirmBtn).toBeInTheDocument();
    });
    const confirmBtn = document.querySelector(
      ".ant-modal-confirm-btns button:last-child",
    );
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api).toHaveBeenCalledWith("POST", "/activity/12/transition", {
        to_status: ACTIVITY_STATUS.archived,
      });
    });

    // Wait for the async ok handler to fully finish and close the modal/slide-in
    await waitFor(() => {
      expect(handleRefresh).toHaveBeenCalled();
      expect(handleClose).toHaveBeenCalled();
    });
  });

  it("renders Edit and Save changes as draft buttons for Draft activity", async () => {
    render(
      <ActivityDetailSlideIn
        activityId={12}
        onClose={jest.fn()}
        onEdit={jest.fn()}
        onRefresh={jest.fn()}
      />,
    );

    await waitFor(() => {
      const footer = document.querySelector(".sticky.bottom-0");
      expect(within(footer).getByText("Edit")).toBeInTheDocument();
      expect(
        within(footer).getByText("Save changes as draft"),
      ).toBeInTheDocument();
    });
  });

  it("does NOT render Edit or Save changes as draft buttons for Active activity", async () => {
    api.mockImplementation((method, url) => {
      if (method === "GET" && url === "/activity/12") {
        return Promise.resolve({
          ...mockActivity,
          status: ACTIVITY_STATUS.active,
        });
      }
      return Promise.resolve({});
    });

    render(
      <ActivityDetailSlideIn
        activityId={12}
        onClose={jest.fn()}
        onEdit={jest.fn()}
        onRefresh={jest.fn()}
      />,
    );

    await waitFor(() => {
      const footer = document.querySelector(".sticky.bottom-0");
      expect(within(footer).queryByText("Edit")).not.toBeInTheDocument();
      expect(
        within(footer).queryByText("Save changes as draft"),
      ).not.toBeInTheDocument();
    });
  });
});
