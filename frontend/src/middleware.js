import { NextResponse } from "next/server";
import { auth } from "./lib";
import { HOME_PAGE, USER_ROLES } from "./static/config";

// route prefix -> where anonymous visitors are sent.
// observers sign in with an emailed magic link, not the password form.
const protectedRoutes = {
  "/activity-library": "/login",
  "/brief-builder": "/login",
  // Only this tab of /detailed-insights is gated; the explorer itself is
  // public, and startsWith matches the subtree rather than the parent.
  "/detailed-insights/risk-level": "/login",
  "/citizen-weather/admin": "/login",
  "/citizen-weather/observe": "/citizen-weather",
  "/profile": "/login",
  "/publications": "/login",
  "/reviews": "/login",
  "/settings": "/login",
  "/validations": "/login",
};
// Sign-in screens. Exact match, not prefix: /citizen-weather is the observer's
// sign-in page but /citizen-weather/observe underneath it is their app.
const authRoutes = ["/login", "/citizen-weather"];

export default async function middleware(request) {
  const session = request.cookies.get("currentUser")?.value;
  const pathName = request.nextUrl.pathname;
  const response = NextResponse.next();

  // prefix match: sub-routes (/publications/create, /citizen-weather/observe/2026-05)
  // are protected too, not just the exact segment
  const signInPath = Object.entries(protectedRoutes).find(([route]) =>
    pathName.startsWith(route),
  )?.[1];

  if (!session && signInPath) {
    return NextResponse.redirect(new URL(signInPath, request.url));
  }
  if (session) {
    const { token: authToken, role, abilities } = await auth.decrypt(session);

    // Validated BEFORE the sign-in-screen redirect below. The other order
    // sent someone holding a dead cookie from /login to their home page,
    // which then bounced them back to /login — two wasted hops that only
    // terminated because the cookie had been cleared on the way past.
    const req = await fetch(
      `${process.env.WEBDOMAIN}/api/v1/users/me?format=json`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
      },
    );
    // The session is dead — expired token, rotated SESSION_SECRET, deleted
    // user. Clearing the cookie is not enough on its own: without the return
    // below, THIS request still rendered the page, and every data fetch in it
    // failed, so the visitor got an empty shell instead of a sign-in prompt.
    //
    // Only gated routes redirect. This middleware runs on public pages too,
    // and bouncing someone off /about because of a stale cookie would be a
    // worse bug than the one being fixed — there, clear it and carry on.
    //
    // `signInPath`, not /unauthorized: an expired session is not a permission
    // failure. The role checks below still send genuinely forbidden users to
    // /unauthorized, but they cannot speak for this case — `decrypt` returns
    // {} for a bad cookie, so `role` is undefined and every one of them would
    // fire for the wrong reason.
    if (!req.ok) {
      const expired = signInPath
        ? NextResponse.redirect(new URL(signInPath, request.url))
        : response;
      expired.cookies.set({
        name: "currentUser",
        value: "",
        httpOnly: true,
        expires: new Date(0),
      });
      return expired;
    }

    // A magic link always wins over the current session — the browser may
    // already hold a different account's cookie, and only the page can
    // exchange the token. Redirecting here would sign them in as the wrong
    // user and silently drop the link.
    const hasMagicLink = request.nextUrl.searchParams.has("token");
    if (authRoutes.includes(pathName) && !hasMagicLink) {
      return NextResponse.redirect(
        new URL(HOME_PAGE[role] || "/profile", request.url),
      );
    }

    // A TWG reviewer may VIEW one Inkhundla's validation decision — the page
    // shows them the panel they are part of — but not the queue index, and
    // not submit (the PUT is admin-only server-side).
    const isDecisionPage = /^\/validations\/\d+\/\d+/.test(pathName);

    // Brief Builder is for both staff roles, so it is gated on "is staff"
    // rather than on one role — an observer must not reach it. Kept as an
    // allow-list of the two staff roles rather than `!== USER_ROLES.observer`
    // so a fourth role added later is denied by default.
    const isStaff = [USER_ROLES.admin, USER_ROLES.reviewer].includes(role);

    // CS-DEL-1: the citizen-science admin page is the one admin surface a
    // non-admin can be delegated. Read off abilities rather than a separate
    // session flag, so the client has ONE authority to consult — the same
    // list the page's own <Can> guards already use.
    const managesCitizenScience = (abilities || []).some(
      (a) => a?.subject === "CitizenScience",
    );

    if (
      role !== USER_ROLES.observer &&
      pathName.startsWith("/citizen-weather/observe")
    ) {
      return NextResponse.redirect(new URL("/unauthorized", request.url));
    }

    if (
      (!isStaff &&
        (pathName.startsWith("/activity-library") ||
          pathName.startsWith("/brief-builder"))) ||
      (role !== USER_ROLES.reviewer && pathName.startsWith("/reviews")) ||
      (role !== USER_ROLES.admin &&
        (pathName.startsWith("/publications") ||
          pathName.startsWith("/settings") ||
          (pathName.startsWith("/validations") && !isDecisionPage))) ||
      // Left the admin-only list above: an admin OR a delegated coordinator.
      (role !== USER_ROLES.admin &&
        !managesCitizenScience &&
        pathName.startsWith("/citizen-weather/admin"))
    ) {
      return NextResponse.redirect(new URL("/unauthorized", request.url));
    }
  }
  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, sitemap.xml, robots.txt (metadata files)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};
