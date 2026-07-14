import React from "react";
import { render, screen } from "@testing-library/react";
import ActivityAddedModal from "../../../components/Modals/ActivityAddedModal";

describe("ActivityAddedModal Component", () => {
  it("renders success messages correctly", () => {
    const handleClose = jest.fn();
    render(<ActivityAddedModal open={true} onClose={handleClose} />);

    expect(screen.getByText("Response activity added!")).toBeInTheDocument();
    expect(screen.getByText("Your activity has been added to the system.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ok/i })).toBeInTheDocument();
  });
});
