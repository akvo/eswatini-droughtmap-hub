import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import PublicationsPage from "../page";
import { api } from "@/lib";
import { useRouter } from "next/navigation";
import { PUBLICATION_STATUS, MAP_CATEGORY_OPTIONS } from "@/static/config";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}));

// Mock api
jest.mock("@/lib", () => ({
  api: jest.fn(),
}));

// Mock Can component to simply render children
jest.mock("@/components", () => {
  const actual = jest.requireActual("@/components");
  return {
    ...actual,
    Can: ({ children }) => <>{children}</>,
    FeedbackSection: () => <div data-testid="feedback-section" />,
  };
});

// Mock AntD responsive observer to avoid issues in testing environment
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

// Mock AntD components to prevent JSDOM nwsapi stylesheet parsing crashes
jest.mock("antd", () => {
  const original = jest.requireActual("antd");
  return {
    ...original,
    Select: ({ options = [], value, onChange }) => (
      <select
        data-testid="mock-select"
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    ),
  };
});

const mockData = {
  current: 1,
  total: 4,
  total_page: 1,
  data: [
    {
      pk: 4021,
      title: "step_0303_cdi_pct_rank_eswatini_202605",
      detail_url: "https://geonode.org/cdi_202605",
      embed_url: "https://geonode.org/cdi_202605/embed",
      thumbnail_url: "https://geonode.org/cdi_202605/thumb.png",
      file_size: "200 KB",
      created: "2026-05-26T12:00:00Z",
      year_month: "2026-05",
      publication_id: null,
      status: null,
    },
    {
      pk: 4022,
      title: "step_0304_cdi_pct_rank_eswatini_202606",
      detail_url: "https://geonode.org/cdi_202606",
      embed_url: "https://geonode.org/cdi_202606/embed",
      thumbnail_url: "https://geonode.org/cdi_202606/thumb.png",
      file_size: "195 KB",
      created: "2026-06-26T12:00:00Z",
      year_month: "2026-06",
      publication_id: 101,
      status: PUBLICATION_STATUS.in_review,
    },
    {
      pk: 4023,
      title: "step_0305_cdi_pct_rank_eswatini_202607",
      detail_url: "https://geonode.org/cdi_202607",
      embed_url: "https://geonode.org/cdi_202607/embed",
      thumbnail_url: "https://geonode.org/cdi_202607/thumb.png",
      file_size: "210 KB",
      created: "2026-07-26T12:00:00Z",
      year_month: "2026-07",
      publication_id: 102,
      status: PUBLICATION_STATUS.in_validation,
    },
    {
      pk: 4024,
      title: "step_0306_cdi_pct_rank_eswatini_202608",
      detail_url: "https://geonode.org/cdi_202608",
      embed_url: "https://geonode.org/cdi_202608/embed",
      thumbnail_url: "https://geonode.org/cdi_202608/thumb.png",
      file_size: "205 KB",
      created: "2026-08-26T12:00:00Z",
      year_month: "2026-08",
      publication_id: 103,
      status: PUBLICATION_STATUS.published,
    },
  ],
};

describe("PublicationsPage", () => {
  let mockPush;

  beforeEach(() => {
    jest.clearAllMocks();
    mockPush = jest.fn();
    useRouter.mockReturnValue({ push: mockPush });
    api.mockResolvedValue(mockData);
  });

  it("loads and displays the header and initial table data", async () => {
    render(<PublicationsPage />);

    expect(screen.getByText("CDI publication")).toBeInTheDocument();
    expect(
      screen.getByText("Manage and track CDI map publications."),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(api).toHaveBeenCalledWith(
        "GET",
        expect.stringContaining("/admin/cdi-geonode"),
      );
    });

    expect(
      screen.getByText("step_0303_cdi_pct_rank_eswatini_202605"),
    ).toBeInTheDocument();
    expect(screen.getByText("200 KB")).toBeInTheDocument();
    expect(screen.getByText("May 2026")).toBeInTheDocument();
  });

  it("filters API requests by status tab", async () => {
    render(<PublicationsPage />);

    await waitFor(() => expect(api).toHaveBeenCalledTimes(1));

    // Click "Awaiting review" tab
    const awaitingTab = screen.getByRole("tab", { name: "Awaiting review" });
    fireEvent.click(awaitingTab);

    await waitFor(() => {
      expect(api).toHaveBeenLastCalledWith(
        "GET",
        expect.stringContaining("status=1"),
      );
    });

    // Click "Ready" tab
    const readyTab = screen.getByRole("tab", { name: "Ready" });
    fireEvent.click(readyTab);

    await waitFor(() => {
      expect(api).toHaveBeenLastCalledWith(
        "GET",
        expect.stringContaining("status=2"),
      );
    });

    // Click "Validated" tab
    const validatedTab = screen.getByRole("tab", { name: "Validated" });
    fireEvent.click(validatedTab);

    await waitFor(() => {
      expect(api).toHaveBeenLastCalledWith(
        "GET",
        expect.stringContaining("status=3"),
      );
    });

    // Click "All" tab
    const allTab = screen.getByRole("tab", { name: "All" });
    fireEvent.click(allTab);

    await waitFor(() => {
      expect(api).toHaveBeenLastCalledWith(
        "GET",
        expect.not.stringContaining("status="),
      );
    });
  });

  it("renders correct status tags color and text", async () => {
    render(<PublicationsPage />);

    await waitFor(() => {
      expect(screen.getByText("Not yet started")).toBeInTheDocument();
      expect(screen.getAllByText("Awaiting review").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Ready").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Validated").length).toBeGreaterThan(0);
    });

    // Check color classes/style or element properties
    const notStartedTag = screen
      .getByText("Not yet started")
      .closest(".ant-tag");
    expect(notStartedTag).toHaveStyle("background-color: rgb(102, 112, 133)"); // #667085 equivalent

    const awaitingTag = screen
      .getAllByText("Awaiting review")
      .find((el) => el.closest(".ant-tag"))
      .closest(".ant-tag");
    expect(awaitingTag).toHaveStyle("background-color: rgb(243, 156, 18)"); // #f39c12 equivalent

    const readyTag = screen
      .getAllByText("Ready")
      .find((el) => el.closest(".ant-tag"))
      .closest(".ant-tag");
    expect(readyTag).toHaveStyle("background-color: rgb(255, 205, 55)"); // #ffcd37 equivalent

    const validatedTag = screen
      .getAllByText("Validated")
      .find((el) => el.closest(".ant-tag"))
      .closest(".ant-tag");
    expect(validatedTag).toHaveStyle("background-color: rgb(18, 183, 106)"); // #12b76a equivalent
  });

  it("renders proper action links and routes on click", async () => {
    render(<PublicationsPage />);

    await waitFor(() => {
      expect(screen.getAllByText("Start new publication").length).toBe(1);
      expect(screen.getAllByText("Validate").length).toBe(3);
    });

    // Click "Start new publication" for first row
    const startNewBtn = screen.getByText("Start new publication");
    fireEvent.click(startNewBtn);
    expect(mockPush).toHaveBeenCalledWith(
      "/publications/create?cdi_geonode_id=4021",
    );

    // Click "Validate" for row in_review status (redirects to publication detail page)
    const validateButtons = screen.getAllByText("Validate");
    fireEvent.click(validateButtons[0]); // row with id 101, status 1
    expect(mockPush).toHaveBeenCalledWith("/publications/101");

    // Click "Validate" for row in_validation status (redirects to validation workflow page)
    fireEvent.click(validateButtons[1]); // row with id 102, status 2
    expect(mockPush).toHaveBeenCalledWith("/publications/102/validation");
  });

  it("opens preview modal on preview link click", async () => {
    render(<PublicationsPage />);

    await waitFor(() => {
      expect(
        screen.getByText("step_0303_cdi_pct_rank_eswatini_202605"),
      ).toBeInTheDocument();
    });

    const previewLink = screen.getByText(
      "step_0303_cdi_pct_rank_eswatini_202605",
    );
    fireEvent.click(previewLink);

    // Verify modal is open
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    const iframe = document.querySelector("iframe");
    expect(iframe).toHaveAttribute(
      "src",
      "https://geonode.org/cdi_202605/embed",
    );
  });

  it("shows fallback text in modal when embed_url is missing", async () => {
    // Modify one record to not have embed_url
    const dataWithoutEmbed = {
      ...mockData,
      data: [
        {
          ...mockData.data[0],
          embed_url: null,
        },
      ],
    };
    api.mockResolvedValue(dataWithoutEmbed);

    render(<PublicationsPage />);

    await waitFor(() => {
      expect(
        screen.getByText("step_0303_cdi_pct_rank_eswatini_202605"),
      ).toBeInTheDocument();
    });

    const previewLink = screen.getByText(
      "step_0303_cdi_pct_rank_eswatini_202605",
    );
    fireEvent.click(previewLink);

    expect(screen.getByText("No preview available")).toBeInTheDocument();
  });

  it("truncates very long titles in the preview column", async () => {
    const longTitle = "a".repeat(110);
    const dataWithLongTitle = {
      ...mockData,
      data: [
        {
          ...mockData.data[0],
          title: longTitle,
        },
      ],
    };
    api.mockResolvedValue(dataWithLongTitle);

    render(<PublicationsPage />);

    await waitFor(() => {
      const truncatedTitle = `${"a".repeat(75)}.....`;
      expect(screen.getByText(truncatedTitle)).toBeInTheDocument();
    });
  });

  it("handles category selection change", async () => {
    render(<PublicationsPage />);

    await waitFor(() => expect(api).toHaveBeenCalledTimes(1));

    const categorySelect = screen.getByTestId("mock-select");
    fireEvent.change(categorySelect, { target: { value: "spi-raster-map" } });

    await waitFor(() => {
      expect(api).toHaveBeenLastCalledWith(
        "GET",
        expect.stringContaining("category=spi-raster-map"),
      );
    });
  });

  it("handles table sorting change", async () => {
    const { container } = render(<PublicationsPage />);

    await waitFor(() => expect(api).toHaveBeenCalledTimes(1));

    // Simulate table onChange triggering sorting on PUBLICATION DATE (year_month)
    const table = container.querySelector(".ant-table-wrapper");
    // Find column header for year_month and click or trigger onChange callback manually
    // Since columns have sorter: true, we can trigger handleTableChange callback via AntD Table's onChange
    // The columns are: CREATED AT, PREVIEW, PUBLICATION DATE, STATUS, ACTIONS.
    // Let's trigger sorting via the header sort trigger
    const sorterHeader = screen.getByText("PUBLICATION DATE");
    fireEvent.click(sorterHeader);

    await waitFor(() => {
      expect(api).toHaveBeenLastCalledWith(
        "GET",
        expect.stringContaining("sort=year_month"),
      );
    });
  });

  it("gracefully handles API fetch errors", async () => {
    const consoleErrorMock = jest
      .spyOn(console, "error")
      .mockImplementation(() => {});
    api.mockRejectedValue(new Error("API Failure"));

    render(<PublicationsPage />);

    await waitFor(() => {
      expect(api).toHaveBeenCalled();
      expect(consoleErrorMock).toHaveBeenCalled();
    });
    consoleErrorMock.mockRestore();
  });
});
