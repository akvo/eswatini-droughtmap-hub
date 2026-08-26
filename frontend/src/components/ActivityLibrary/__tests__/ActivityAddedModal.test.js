import React from "react";
import { render, screen } from "@testing-library/react";
import ActivityAddedModal from "../../../components/Modals/ActivityAddedModal";

describe("ActivityAddedModal Component", () => {
  it("renders success messages correctly", () => {
    const handleClose = jest.fn();
    render(<ActivityAddedModal open={true} onClose={handleClose} />);

    expect(screen.getByText("Response activity added!")).toBeInTheDocument();
    expect(
      screen.getByText("Your activity has been added to the system."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ok/i })).toBeInTheDocument();
  });

  it("says updated, not added, in the edit flow", () => {
    render(<ActivityAddedModal open={true} onClose={jest.fn()} isEdit />);

    expect(screen.getByText("Response activity updated!")).toBeInTheDocument();
    expect(
      screen.getByText("Your changes have been saved."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/added/i)).not.toBeInTheDocument();
  });

  it("lets an explicit subtitle win over the default", () => {
    render(
      <ActivityAddedModal
        open={true}
        onClose={jest.fn()}
        subtitle="Activity created as Draft."
      />,
    );

    expect(screen.getByText("Activity created as Draft.")).toBeInTheDocument();
  });
});
