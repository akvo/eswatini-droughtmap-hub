import React from "react";
import { render, screen } from "@testing-library/react";
import AddActivitySlideIn from "../AddActivity/AddActivitySlideIn";

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

describe("AddActivitySlideIn Component", () => {
  it("renders Step 1 (Identify) fields", () => {
    const handleClose = jest.fn();
    const handleSuccess = jest.fn();

    render(
      <AddActivitySlideIn
        visible={true}
        onClose={handleClose}
        onSuccess={handleSuccess}
      />,
    );

    // Assert using getByText queries to avoid the nwsapi role compilation bug
    expect(screen.getByText("Identity")).toBeInTheDocument();
    expect(screen.getByText("Protocol ID")).toBeInTheDocument();
    expect(screen.getByText("Title *")).toBeInTheDocument();
    expect(screen.getByText("Description *")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(
        "please write a description of the activity you are adding.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Next")).toBeInTheDocument();
  });
});
