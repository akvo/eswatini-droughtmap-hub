import { render, waitFor } from "@testing-library/react";
import Home from "../page";

it("renders homepage unchanged", async () => {
  await waitFor(() => {
    const { container } = render(<Home />);
    expect(container).toMatchSnapshot();
  });
});
