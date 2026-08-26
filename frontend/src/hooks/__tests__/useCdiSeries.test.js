import { act, renderHook, waitFor } from "@testing-library/react";
import useCdiSeries from "../useCdiSeries";
import { api } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  api: jest.fn(),
}));

const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

const SERIES = { data: [{ key: "spi", data: [] }], meta: { months: 12 } };

describe("useCdiSeries", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("sends only the params it was given", async () => {
    api.mockResolvedValue(SERIES);
    renderHook(() =>
      useCdiSeries(4588078, {
        from: "2025-08",
        to: "2026-07",
        indicators: "spi",
      }),
    );

    await waitFor(() => expect(api).toHaveBeenCalledTimes(1));
    expect(api).toHaveBeenCalledWith(
      "GET",
      "/cdi/administrations/4588078/series" +
        "?from=2025-08&to=2026-07&indicators=spi",
    );
  });

  it("omits the query entirely when no range or indicator is given", async () => {
    api.mockResolvedValue(SERIES);
    renderHook(() => useCdiSeries(4588078));

    await waitFor(() => expect(api).toHaveBeenCalledTimes(1));
    expect(api).toHaveBeenCalledWith(
      "GET",
      "/cdi/administrations/4588078/series",
    );
  });

  it("keeps `from` when `to` is absent — the backend fills the other end", async () => {
    api.mockResolvedValue(SERIES);
    renderHook(() => useCdiSeries(4588078, { from: "2025-08" }));

    await waitFor(() => expect(api).toHaveBeenCalledTimes(1));
    expect(api).toHaveBeenCalledWith(
      "GET",
      "/cdi/administrations/4588078/series?from=2025-08",
    );
  });

  it("does not fetch, and holds no data, without an administration", async () => {
    const { result } = renderHook(() => useCdiSeries(null));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(api).not.toHaveBeenCalled();
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  // Flush microtasks AND a macrotask: the response travels through several
  // promise hops before it reaches setState, so a bare `await Promise
  // .resolve()` returns before a stale write would have landed — which made
  // an earlier version of this test pass even with the guard removed.
  const settle = () =>
    act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

  it("ignores a slow response superseded by a newer range", async () => {
    const slow = deferred();
    const fast = deferred();
    api.mockReturnValueOnce(slow.promise).mockReturnValueOnce(fast.promise);

    const { result, rerender } = renderHook(
      ({ range }) => useCdiSeries(4588078, range),
      { initialProps: { range: { from: "2025-01", to: "2025-12" } } },
    );
    await waitFor(() => expect(api).toHaveBeenCalledTimes(1));

    // Picker moved before the first response landed.
    rerender({ range: { from: "2026-01", to: "2026-07" } });
    await waitFor(() => expect(api).toHaveBeenCalledTimes(2));

    const newer = { ...SERIES, meta: { months: 7 } };
    fast.resolve(newer);
    await waitFor(() => expect(result.current.data).toEqual(newer));

    // The stale one lands last and must not win.
    slow.resolve({ ...SERIES, meta: { months: 12 } });
    await settle();
    expect(result.current.data).toEqual(newer);
  });

  it("stops loading from a superseded request clobbering the current one", async () => {
    const slow = deferred();
    const fast = deferred();
    api.mockReturnValueOnce(slow.promise).mockReturnValueOnce(fast.promise);

    const { result, rerender } = renderHook(
      ({ range }) => useCdiSeries(4588078, range),
      { initialProps: { range: { from: "2025-01", to: "2025-12" } } },
    );
    await waitFor(() => expect(api).toHaveBeenCalledTimes(1));
    rerender({ range: { from: "2026-01", to: "2026-07" } });
    await waitFor(() => expect(api).toHaveBeenCalledTimes(2));

    // The superseded request finishes FIRST. Its `finally` must not clear the
    // spinner while the request actually on screen is still in flight.
    slow.resolve({ ...SERIES, meta: { months: 12 } });
    await settle();
    expect(result.current.loading).toBe(true);

    fast.resolve({ ...SERIES, meta: { months: 7 } });
    await waitFor(() => expect(result.current.loading).toBe(false));
  });

  it("surfaces the error and clears stale data on failure", async () => {
    const failure = new Error("boom");
    api.mockRejectedValue(failure);

    const { result } = renderHook(() =>
      useCdiSeries(4588078, { indicators: "spi" }),
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe(failure);
    expect(result.current.data).toBeNull();
  });
});
