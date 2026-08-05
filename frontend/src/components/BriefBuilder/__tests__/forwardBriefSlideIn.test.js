import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ForwardBriefSlideIn from "../ForwardBriefSlideIn";
import useBriefRecipients from "@/hooks/useBriefRecipients";
import { api } from "@/lib/api";

jest.mock("@/hooks/useBriefRecipients");
jest.mock("@/lib/api");

const mockRecipients = [
  {
    id: 1,
    name: "Sibusiso Dlamini",
    email: "sibusiso@ndma.gov.sz",
    group: "NDMA",
  },
  {
    id: 2,
    name: "Nokuthula Simelane",
    email: "nokuthula@moa.gov.sz",
    group: "MoAg",
  },
  { id: 3, name: "Thabo Maseko", email: "thabo@met.gov.sz", group: "MET" },
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
      data: mockRecipients,
      loading: false,
      isFallback: false,
    });
  });

  it("does not render when visible is false", () => {
    const { container } = render(
      <ForwardBriefSlideIn {...defaultProps} visible={false} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders recipient roster and Inkhundla summary when visible", () => {
    render(<ForwardBriefSlideIn {...defaultProps} />);
    expect(screen.getByText("Forward brief")).toBeInTheDocument();
    expect(screen.getByText(/Sibusiso Dlamini/i)).toBeInTheDocument();
    expect(screen.getByText(/Nokuthula Simelane/i)).toBeInTheDocument();
    expect(screen.getByText(/Thabo Maseko/i)).toBeInTheDocument();
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
      "/api/v1/brief/forward",
      expect.anything(),
    );
  });

  it("sends payload to POST /brief/forward when recipient is selected", async () => {
    api.mockResolvedValueOnce({ status: "queued" });

    render(<ForwardBriefSlideIn {...defaultProps} />);

    // Select first recipient
    const recipientCheckbox = screen.getByText(/Sibusiso Dlamini/i);
    fireEvent.click(recipientCheckbox);

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
          recipients: [
            { email: "sibusiso@ndma.gov.sz", name: "Sibusiso Dlamini" },
          ],
        }),
      );
    });

    expect(defaultProps.onClose).toHaveBeenCalled();
  });
});
