import React from "react";
import { render, screen, act } from "@testing-library/react";
import BriefContextProvider, { useBrief } from "@/context/BriefContextProvider";
import { api } from "@/lib/api";

jest.mock("@/lib/api");

let searchParams = new URLSearchParams("inkhundla=1&components=cover_header");
const replace = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/brief-builder",
  useSearchParams: () => searchParams,
}));

// A window into the context, so the narrative rules can be exercised without
// mounting TinyMCE.
let ctx;
const Probe = () => {
  ctx = useBrief();
  return <span data-testid="narrative">{ctx.narrative}</span>;
};

const renderProvider = () =>
  render(
    <BriefContextProvider>
      <Probe />
    </BriefContextProvider>,
  );

describe("brief narrative state", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    api.mockResolvedValue([]);
    searchParams = new URLSearchParams("inkhundla=1&components=cover_header");
  });

  it("keeps the draft marked as generated when TinyMCE reformats it", async () => {
    await act(async () => {
      renderProvider();
    });

    await act(async () => ctx.seedNarrative("Gege is validated at D4."));
    // What TinyMCE emits on mount: same words, its own markup.
    await act(async () => ctx.setNarrative("<p>Gege is validated at D4.</p>"));

    expect(ctx.narrativeEdited).toBe(false);
  });

  it("marks the draft as edited once the words actually change", async () => {
    await act(async () => {
      renderProvider();
    });

    await act(async () => ctx.seedNarrative("Gege is validated at D4."));
    await act(async () =>
      ctx.setNarrative("<p>Gege is validated at D4. Rewritten by the TWG.</p>"),
    );

    expect(ctx.narrativeEdited).toBe(true);
  });

  it("clears the narrative when the applied Inkhundla changes", async () => {
    const { rerender } = renderProvider();
    await act(async () => {
      rerender(
        <BriefContextProvider>
          <Probe />
        </BriefContextProvider>,
      );
    });

    await act(async () => ctx.seedNarrative("Gege is validated at D4."));
    expect(screen.getByTestId("narrative")).toHaveTextContent("Gege");

    // Apply a different Inkhundla.
    searchParams = new URLSearchParams("inkhundla=2&components=cover_header");
    await act(async () => {
      rerender(
        <BriefContextProvider>
          <Probe />
        </BriefContextProvider>,
      );
    });

    expect(screen.getByTestId("narrative")).toHaveTextContent("");
    expect(ctx.narrativeEdited).toBe(false);
  });

  it("clears an EDITED narrative too — carrying it over is the worse bug", async () => {
    const { rerender } = renderProvider();
    await act(async () => {
      rerender(
        <BriefContextProvider>
          <Probe />
        </BriefContextProvider>,
      );
    });

    await act(async () => ctx.seedNarrative("Gege is validated at D4."));
    await act(async () =>
      ctx.setNarrative("<p>Hand-written by a reviewer.</p>"),
    );
    expect(ctx.narrativeEdited).toBe(true);

    searchParams = new URLSearchParams("inkhundla=2&components=cover_header");
    await act(async () => {
      rerender(
        <BriefContextProvider>
          <Probe />
        </BriefContextProvider>,
      );
    });

    expect(screen.getByTestId("narrative")).toHaveTextContent("");
    expect(ctx.narrativeEdited).toBe(false);
  });
});
