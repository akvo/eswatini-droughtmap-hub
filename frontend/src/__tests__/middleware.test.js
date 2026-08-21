import middleware from "../middleware";
import { auth } from "@/lib";

jest.mock("next/server", () => ({
  NextResponse: {
    next: () => ({ type: "next", cookies: { set: jest.fn() } }),
    redirect: (url) => ({
      type: "redirect",
      to: url.pathname,
      cookies: { set: jest.fn() },
    }),
  },
}));

jest.mock("@/lib", () => ({
  auth: { decrypt: jest.fn() },
}));

const ROLES = { admin: 1, reviewer: 2, observer: 3 };

// /users/me is called for every authenticated request. The stub used to be a
// permanent `{ ok: true }` with a comment saying a non-ok response "only
// clears the cookie" — which was true, and was the bug: the request then
// rendered the page anyway. It is settable per test now so the dead-session
// path is actually exercised.
global.fetch = jest.fn();

beforeEach(() => global.fetch.mockResolvedValue({ ok: true }));

const request = (pathname, { session, search = "" } = {}) => ({
  cookies: { get: () => (session ? { value: "cookie" } : undefined) },
  nextUrl: { pathname, searchParams: new URLSearchParams(search) },
  url: `http://localhost:3000${pathname}${search ? `?${search}` : ""}`,
});

const run = async (pathname, opts) => middleware(request(pathname, opts));

describe("middleware", () => {
  beforeEach(() => jest.clearAllMocks());

  describe("signed-in visitors are sent off the sign-in screens", () => {
    it.each([
      [
        "observer",
        "/citizen-weather",
        "/citizen-weather/observe",
        ROLES.observer,
      ],
      ["observer", "/login", "/citizen-weather/observe", ROLES.observer],
      ["admin", "/citizen-weather", "/publications", ROLES.admin],
      ["reviewer", "/login", "/reviews", ROLES.reviewer],
    ])("%s on %s -> %s", async (_label, from, to, role) => {
      auth.decrypt.mockResolvedValue({ token: "t", role });
      expect(await run(from, { session: true })).toMatchObject({
        type: "redirect",
        to,
      });
    });
  });

  it("leaves the observer app itself alone — authRoutes is exact, not prefix", async () => {
    auth.decrypt.mockResolvedValue({ token: "t", role: ROLES.observer });
    expect(
      (await run("/citizen-weather/observe", { session: true })).type,
    ).toBe("next");
  });

  it("lets a magic link through an existing session", async () => {
    // the cookie may belong to a different account, and only the page can
    // exchange the token — redirecting would drop the link silently
    auth.decrypt.mockResolvedValue({ token: "t", role: ROLES.admin });
    expect(
      (await run("/citizen-weather", { session: true, search: "token=abc" }))
        .type,
    ).toBe("next");
  });

  describe("anonymous visitors", () => {
    it.each([
      ["/citizen-weather/observe", "/citizen-weather"],
      ["/citizen-weather/observe/2026-05", "/citizen-weather"],
      ["/citizen-weather/admin", "/login"],
      ["/publications/create", "/login"],
    ])("%s -> %s", async (from, to) => {
      expect(await run(from)).toMatchObject({ type: "redirect", to });
    });

    it.each(["/citizen-weather", "/login"])("%s stays public", async (path) => {
      expect((await run(path)).type).toBe("next");
    });
  });

  describe("a session cookie that no longer validates", () => {
    // decrypt() swallows a bad cookie and returns {}, so `role` is undefined.
    // Most gated routes only escaped by accident, because some role check
    // fired on that undefined and sent them to /unauthorized — the wrong
    // destination for an expired session, and no help at all to the two
    // routes below that have no role check to fire.
    beforeEach(() => {
      auth.decrypt.mockResolvedValue({});
      global.fetch.mockResolvedValue({ ok: false, status: 401 });
    });

    it.each([
      // No role check: it used to render an empty, data-less page.
      ["/profile", "/login"],
      // Exempt from the admin check so a TWG reviewer can view one decision
      // — which is why a dead session reached the browser here too.
      ["/validations/27/4564328", "/login"],
      ["/publications", "/login"],
      ["/reviews/85/4564328", "/login"],
      ["/activity-library", "/login"],
      ["/settings", "/login"],
      ["/brief-builder", "/login"],
      ["/citizen-weather/admin", "/login"],
      ["/citizen-weather/observe", "/citizen-weather"],
    ])("%s -> %s instead of rendering empty", async (from, to) => {
      const res = await run(from, { session: true });
      expect(res).toMatchObject({ type: "redirect", to });
    });

    it("clears the dead cookie on the way out", async () => {
      const res = await run("/profile", { session: true });
      expect(res.cookies.set).toHaveBeenCalledWith(
        expect.objectContaining({ name: "currentUser", value: "" }),
      );
    });

    it.each(["/", "/about", "/methodology", "/detailed-insights"])(
      "%s still renders — a stale cookie is no reason to bounce a public page",
      async (path) => {
        expect((await run(path, { session: true })).type).toBe("next");
      },
    );

    it("renders /login rather than bouncing via the home page", async () => {
      // The session is validated BEFORE the sign-in-screen redirect. The
      // other order sent them to their home page, which bounced straight
      // back here — two hops that only ended because the cookie was cleared
      // in passing.
      expect((await run("/login", { session: true })).type).toBe("next");
    });
  });
});
