import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import AppContextProvider, {
  useAppDispatch,
} from "../../../context/AppContextProvider";
import ReviewAdmModal from "../ReviewAdmModal";
import { api } from "../../../lib";

jest.mock("../../../lib", () => ({ api: jest.fn() }));

jest.setTimeout(30000);

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
  fn.default = mockObserver; // Make default the object or function to satisfy different import specs
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
  };
});

const detail = {
  administration: {
    administration_id: 7,
    name: "Piggs peak",
    region: "Hhohho",
    cdi_class: 3,
    confidence: { value: 4.2, band: "high", is_mock: true },
    reviews: { completed: 1, total: 2 },
    disputed: false,
  },
  my_review: { review_id: 11, suggestion: null },
};

const review = {
  id: 11,
  is_completed: false,
  suggestion_values: null,
  publication: {
    initial_values: [
      { administration_id: 7, category: 3 },
      { administration_id: 8, category: 1 },
    ],
  },
};

/** The app opens the modal by dispatching SET_ACTIVE_ADM *after* mount. */
const Harness = ({ onSubmitted }) => {
  const dispatch = useAppDispatch();
  return (
    <>
      <button
        type="button"
        onClick={() =>
          dispatch({
            type: "SET_ACTIVE_ADM",
            payload: { administration_id: 7, name: "Piggs peak" },
          })
        }
      >
        open
      </button>
      <ReviewAdmModal
        review={review}
        publicationId={4}
        onSubmitted={onSubmitted}
      />
    </>
  );
};

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query) => ({
      matches: false,
      media: query,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    }),
  });
});

beforeEach(() => {
  jest.clearAllMocks();
  api.mockImplementation((method) =>
    method === "GET" ? Promise.resolve(detail) : Promise.resolve({}),
  );
});

const open = async () => {
  fireEvent.click(screen.getByRole("button", { name: "open" }));
  // Wait until the API response has loaded and the "Approve" button is enabled.
  // "Piggs peak" appears immediately from context state, but the button stays
  // disabled (loading=true) until loadDetail resolves, so we wait for the
  // button to become interactable instead.
  await waitFor(() => {
    const btn = screen.getByRole("button", { name: /approve computed value/i });
    expect(btn).not.toBeDisabled();
  });
};

it("approves the computed value with a single review PUT", async () => {
  const onSubmitted = jest.fn();
  render(
    <AppContextProvider>
      <Harness onSubmitted={onSubmitted} />
    </AppContextProvider>,
  );

  await open();
  fireEvent.click(
    screen.getByRole("button", { name: /approve computed value/i }),
  );

  await waitFor(() => {
    expect(api).toHaveBeenCalledWith("PUT", "/reviewer/review/11", {
      suggestion_values: [
        { administration_id: 7, category: 3, comment: "", reviewed: true },
        { administration_id: 8, category: 1 },
      ],
    });
  });
  expect(onSubmitted).toHaveBeenCalled();
});

// Normal/wet is category 0 — a computed value, not a missing one. Treating it
// as missing forced the modal into suggest mode and blocked a plain approval.
it("approves a normal (category 0) Inkhundla instead of forcing a suggestion", async () => {
  api.mockImplementation((method) =>
    method === "GET"
      ? Promise.resolve({
          ...detail,
          administration: { ...detail.administration, cdi_class: 0 },
        })
      : Promise.resolve({}),
  );

  render(
    <AppContextProvider>
      <Harness onSubmitted={jest.fn()} />
    </AppContextProvider>,
  );

  await open();
  fireEvent.click(
    screen.getByRole("button", { name: /approve computed value/i }),
  );

  await waitFor(() => {
    expect(api).toHaveBeenCalledWith("PUT", "/reviewer/review/11", {
      suggestion_values: [
        { administration_id: 7, category: 0, comment: "", reviewed: true },
        { administration_id: 8, category: 1 },
      ],
    });
  });
});
