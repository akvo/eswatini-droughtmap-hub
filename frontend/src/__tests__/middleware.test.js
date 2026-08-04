import middleware from "../middleware";
import { auth } from "@/lib";

jest.mock("next/server", () => ({
  NextResponse: {
    next: () => ({ type: "next", cookies: { set: jest.fn() } }),
    redirect: (url) => ({ type: "redirect", to: url.pathname }),
  },
}));

jest.mock("@/lib", () => ({
  auth: { decrypt: jest.fn() },
}));

const ROLES = { admin: 1, reviewer: 2, observer: 3 };

// /users/me is called for every authenticated request; a non-ok response only
// clears the cookie, so an ok stub keeps these cases about routing.
global.fetch = jest.fn().mockResolvedValue({ ok: true });

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
      expect(await run(from, { session: true })).toEqual({
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
      expect(await run(from)).toEqual({ type: "redirect", to });
    });

    it.each(["/citizen-weather", "/login"])("%s stays public", async (path) => {
      expect((await run(path)).type).toBe("next");
    });
  });
});
