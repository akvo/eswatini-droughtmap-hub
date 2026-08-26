import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ForwardBriefSlideIn from "../ForwardBriefSlideIn";
import useBriefRecipients from "@/hooks/useBriefRecipients";
import { api } from "@/lib/api";

jest.mock("@/hooks/useBriefRecipients");
jest.mock("@/lib/api");

// The shape /admin/reviewers-tree returns: TWG groups whose children carry the
// name as `title` and the address as `subtitle`. The component no longer builds
// this grouping itself (BB-3 D-4).
const mockTree = [
  {
    value: "twg-1",
    title: "NDMA (National Disaster Management Agency)",
    selectable: false,
    children: [
      {
        value: 1,
        title: "Sibusiso Dlamini",
        subtitle: "sibusiso@ndma.gov.sz",
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
        value: 2,
        title: "Nokuthula Simelane",
        subtitle: "nokuthula@moa.gov.sz",
        selectable: true,
      },
      {
        value: 3,
        title: "Thabo Maseko",
        subtitle: "thabo@met.gov.sz",
        selectable: true,
      },
    ],
  },
];

describe("ForwardBriefSlideIn Component", () => {
  const defaultProps = {
    visible: true,
    onClose: jest.fn(),
    administrationId: 4588078,
    inkhundla: "Gege",
    period: "2026-03",
    components: ["cover_header", "kpi_tiles"],
  };

  beforeEach(() => {
    jest.clearAllMocks();
    useBriefRecipients.mockReturnValue({
      tree: mockTree,
      loading: false,
    });
  });

  it("does not render when visible is false", () => {
    const { container } = render(
      <ForwardBriefSlideIn {...defaultProps} visible={false} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders TreeSelect placeholder and Inkhundla summary when visible", () => {
    render(<ForwardBriefSlideIn {...defaultProps} />);
    expect(screen.getByText("Forward brief")).toBeInTheDocument();
    expect(
      screen.getAllByText("Select TWG or team member")[0],
    ).toBeInTheDocument();
  });

  it("shows validation error when Send is clicked without selecting recipients", async () => {
    render(<ForwardBriefSlideIn {...defaultProps} />);
    const sendBtn = screen.getByText("Send");
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(
        screen.getByText("Choose at least one recipient."),
      ).toBeInTheDocument();
    });
    expect(api).not.toHaveBeenCalledWith(
      "POST",
      "/brief/forward",
      expect.anything(),
    );
  });

  it("sends payload to POST /brief/forward when custom email is provided", async () => {
    api.mockResolvedValueOnce({ status: "queued" });

    render(<ForwardBriefSlideIn {...defaultProps} />);

    const otherInput = screen.getByPlaceholderText("Email address");
    fireEvent.change(otherInput, { target: { value: "custom@domain.com" } });

    const sendBtn = screen.getByText("Send");
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(api).toHaveBeenCalledWith(
        "POST",
        "/brief/forward",
        expect.objectContaining({
          inkhundla_id: 4588078,
          inkhundla_name: "Gege",
          components: ["cover_header", "kpi_tiles"],
          recipients: [{ email: "custom@domain.com", name: "Other" }],
        }),
      );
    });

    expect(defaultProps.onClose).toHaveBeenCalled();
  });
});
