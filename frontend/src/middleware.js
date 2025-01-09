import { NextResponse } from "next/server";
import { decrypt } from "./lib";

const protectedRoutes = ["/profile"];
const authRoutes = ["/login"];

export default async function middleware(request) {
  const session = request.cookies.get("currentUser")?.value;
  const pathName = request.nextUrl.pathname;

  if (!session && protectedRoutes.includes(pathName)) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (session) {
    if (authRoutes.includes(pathName)) {
      return NextResponse.redirect(new URL("/profile", request.url));
    }
    const { token: authToken } = await decrypt(session);
    const req = await fetch(
      `${process.env.WEBDOMAIN}/api/v1/users/me?format=json`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
      }
    );
    if (!req.ok) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
  }
  const response = NextResponse.next();
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
