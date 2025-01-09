import { render } from "@testing-library/react";
import { Navbar } from "../page";

describe("HomePage", () => {
  it("renders login button when session empty", () => {
    const { getByText } = render(<Navbar />);
    expect(getByText("Login")).toBeInTheDocument();
  });

  it("renders profile button when session exists", () => {
    const { getByText } = render(<Navbar session={{ id: 1 }} />);

    expect(getByText("Profile")).toBeInTheDocument();
  });

  it("renders correctly & match with the snapshot", () => {
    const { container } = render(<Navbar session={{ id: 1 }} />);
    expect(container).toMatchSnapshot();
  });
});
