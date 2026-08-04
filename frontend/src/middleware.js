import { NextResponse } from "next/server";
import { auth } from "./lib";
import { HOME_PAGE, USER_ROLES } from "./static/config";

// route prefix -> where anonymous visitors are sent.
// observers sign in with an emailed magic link, not the password form.
const protectedRoutes = {
  "/brief-builder": "/login",
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
    const { token: authToken, role } = await auth.decrypt(session);

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
    if (!req.ok) {
      response.cookies.set({
        name: "currentUser",
        value: "",
        httpOnly: true,
        expires: new Date(0),
      });
    }

    // A TWG reviewer may VIEW one Inkhundla's validation decision — the page
    // shows them the panel they are part of — but not the queue index, and
    // not submit (the PUT is admin-only server-side).
    const isDecisionPage = /^\/validations\/\d+\/\d+/.test(pathName);

    // Brief Builder is for both staff roles, so it is gated on "not an
    // observer" rather than on one role. USER_ROLES has no observer entry —
    // observers are role 3 backend-side — so the test is by exclusion.
    const isStaff = [USER_ROLES.admin, USER_ROLES.reviewer].includes(role);

    if (
      role !== USER_ROLES.observer &&
      pathName.startsWith("/citizen-weather/observe")
    ) {
      return NextResponse.redirect(new URL("/unauthorized", request.url));
    }

    if (
      (!isStaff && pathName.startsWith("/brief-builder")) ||
      (role !== USER_ROLES.reviewer && pathName.startsWith("/reviews")) ||
      (role !== USER_ROLES.admin &&
        (pathName.startsWith("/publications") ||
          pathName.startsWith("/settings") ||
          pathName.startsWith("/citizen-weather/admin") ||
          (pathName.startsWith("/validations") && !isDecisionPage)))
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
