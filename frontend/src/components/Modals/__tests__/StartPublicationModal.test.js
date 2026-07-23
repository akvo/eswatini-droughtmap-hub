/* eslint-disable react/display-name */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import StartPublicationModal from "../StartPublicationModal";
import { api } from "@/lib";
import dayjs from "dayjs";

jest.setTimeout(20000);

jest.mock("@/lib", () => ({
  api: jest.fn(),
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

jest.mock("antd", () => {
  const original = jest.requireActual("antd");
  return {
    ...original,
    message: {
      error: jest.fn(),
      success: jest.fn(),
      warning: jest.fn(),
      info: jest.fn(),
    },
    TreeSelect: React.forwardRef(
      (
        {
          value,
          onChange,
          placeholder,
          treeData,
          id,
          treeCheckable,
          showCheckedStrategy,
          treeNodeLabelProp,
          treeNodeFilterProp,
          showSearch,
          labelRender,
          ...rest
        },
        ref,
      ) => (
        <select
          ref={ref}
          id={id}
          data-testid="mock-tree-select"
          value={value || []}
          multiple
          onChange={(e) => {
            let vals;
            if (
              e.target.selectedOptions &&
              e.target.selectedOptions.length > 0
            ) {
              vals = Array.from(e.target.selectedOptions).map((o) =>
                parseInt(o.value, 10),
              );
            } else if (Array.isArray(e.target.value)) {
              vals = e.target.value.map((v) => parseInt(v, 10));
            } else {
              vals = [parseInt(e.target.value, 10)];
            }
            onChange?.(vals);
          }}
          {...rest}
        >
          {treeData?.map((group) => (
            <optgroup key={group.value} label={group.title}>
              {group.children?.map((child) => (
                <option key={child.value} value={child.value}>
                  {child.title}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      ),
    ),
    DatePicker: React.forwardRef(
      ({ value, onChange, placeholder, id, picker, ...rest }, ref) => (
        <input
          ref={ref}
          id={id}
          type="date"
          data-testid="mock-date-picker"
          value={
            value
              ? typeof value.format === "function"
                ? value.format("YYYY-MM-DD")
                : dayjs(value).format("YYYY-MM-DD")
              : ""
          }
          onChange={(e) => {
            console.log(
              "DatePicker onChange called with value:",
              e.target.value,
              "has onChange prop:",
              !!onChange,
            );
            onChange?.(e.target.value ? dayjs(e.target.value) : null);
          }}
          {...rest}
        />
      ),
    ),
  };
});

// Mock TinyEditor component to avoid tinymce setup in jsdom
jest.mock("../../TinyEditor", () => {
  return function MockTinyEditor({ value, setValue }) {
    return (
      <textarea
        data-testid="mock-tiny-editor"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
    );
  };
});

// Mock ComponentRasterPreview to avoid API fetch
jest.mock("../../ComponentRasterPreview", () => {
  return function MockComponentRasterPreview({ yearMonth }) {
    return (
      <div data-testid="raster-preview">
        Raster Preview for {yearMonth ? yearMonth.format("YYYY-MM") : "none"}
      </div>
    );
  };
});

const mockReviewersTree = [
  {
    value: "twg-1",
    title: "NDMA (National Disaster Management Agency)",
    selectable: false,
    children: [
      {
        value: 12,
        title: "Jane Dlamini",
        subtitle: "jane@ndma.gov.sz",
        email_verified: true,
        selectable: true,
      },
    ],
  },
  {
    value: "twg-2",
    title: "MoAg (Ministry of Agriculture)",
    selectable: false,
    children: [
      {
        value: 15,
        title: "Peter Mamba",
        subtitle: "peter@moag.gov.sz",
        email_verified: true,
        selectable: true,
      },
    ],
  },
  {
    value: "twg-unassigned",
    title: "Unassigned",
    selectable: false,
    children: [
      {
        value: 7,
        title: "John Nkosi",
        subtitle: "john@reviewer.sz",
        email_verified: false,
        selectable: true,
      },
    ],
  },
];

const mockGeonode = {
  pk: 4021,
  title: "step_0303_cdi_pct_rank_eswatini_202605",
  year_month: "2026-05-01",
  download_url: "https://geonode.org/cdi_202605/download",
};

describe("StartPublicationModal", () => {
  let onClose;
  let onSuccess;

  beforeEach(() => {
    jest.clearAllMocks();
    onClose = jest.fn();
    onSuccess = jest.fn();
    api.mockImplementation((method, url) => {
      if (method === "GET" && url === "/admin/reviewers-tree") {
        return Promise.resolve(mockReviewersTree);
      }
      return Promise.resolve({});
    });
  });

  it("does not render when open is false", () => {
    render(
      <StartPublicationModal
        geonode={mockGeonode}
        open={false}
        onClose={onClose}
        onSuccess={onSuccess}
      />,
    );
    expect(
      screen.queryByText("Create new publication"),
    ).not.toBeInTheDocument();
  });

  it("renders form elements and fetches reviewer tree when open is true", async () => {
    render(
      <StartPublicationModal
        geonode={mockGeonode}
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
      />,
    );

    expect(screen.getByText("Create new publication")).toBeInTheDocument();
    expect(api).toHaveBeenCalledWith("GET", "/admin/reviewers-tree");

    await waitFor(() => {
      expect(screen.getByTestId("mock-tree-select")).toBeInTheDocument();
    });

    expect(screen.getByLabelText("Subject")).toHaveValue(
      "CDI Map review requested for month 2026-05",
    );
  });

  it("submits the form successfully and triggers onSuccess", async () => {
    api.mockImplementation((method, url, payload) => {
      if (method === "GET" && url === "/admin/reviewers-tree") {
        return Promise.resolve(mockReviewersTree);
      }
      if (method === "POST" && url === "/admin/publications") {
        return Promise.resolve({ id: 101 });
      }
      return Promise.resolve({});
    });

    render(
      <StartPublicationModal
        geonode={mockGeonode}
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
      />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("mock-tree-select")).toBeInTheDocument();
    });

    // Select reviewer option (needs at least 2 from different TWGs)
    const treeSelect = screen.getByTestId("mock-tree-select");
    const option1 = screen.getByText("Jane Dlamini");
    const option2 = screen.getByText("Peter Mamba");
    option1.selected = true;
    option2.selected = true;
    fireEvent.change(treeSelect);

    // Populate due date
    const dueDateInput = screen.getByLabelText("Review Deadline");
    fireEvent.change(dueDateInput, { target: { value: "2026-06-15" } });

    // Wait for the form validation to pass and the button to be enabled
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Create" })).not.toBeDisabled();
    });

    // Submit the form by clicking Create
    const createBtn = screen.getByRole("button", { name: "Create" });
    fireEvent.click(createBtn);

    await waitFor(() => {
      expect(api).toHaveBeenCalledWith(
        "POST",
        "/admin/publications",
        expect.objectContaining({
          cdi_geonode_id: 4021,
          reviewers: [12, 15],
          due_date: "2026-06-15",
          year_month: "2026-05-01",
        }),
      );
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("calls onClose when Cancel is clicked", async () => {
    render(
      <StartPublicationModal
        geonode={mockGeonode}
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalled();
  });
});
