import { render, screen, waitFor } from "@testing-library/react";
import Home from "../page";

describe("Homepage", () => {
  it("renders a Map", async () => {
    await waitFor(() => {
      render(<Home />);
      const map = screen.getByRole("figure");
      expect(map).toBeInTheDocument();
    });
  });
});
