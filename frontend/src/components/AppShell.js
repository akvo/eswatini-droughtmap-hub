"use client";

import { usePathname } from "next/navigation";
import { Footer, LogoSection, Navbar } from "@/components";

const AppShell = ({ session, children }) => {
  const pathname = usePathname();

  // Embedded maps (compare slider) render bare — no navbar, footer or container.
  // ponytail: /citizen-weather is the standalone observer surface, but its
  // /admin subtree is staff-facing and keeps the normal navbar/footer.
  const isBareCitizenWeather =
    pathname?.startsWith("/citizen-weather") &&
    !pathname?.startsWith("/citizen-weather/admin");

  if (pathname?.startsWith("/iframe") || isBareCitizenWeather) {
    return children;
  }

  return (
    <>
      <div className="w-full min-h-screen bg-white flex flex-col overflow-x-hidden">
        <Navbar session={session} />
        <div className="container w-full h-full relative space-y-4 xl:space-y-8 pt-3 pb-9 bg-white">
          {children}
        </div>
        <LogoSection />
      </div>
      <Footer />
    </>
  );
};

export default AppShell;
