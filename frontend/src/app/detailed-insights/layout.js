import { auth } from "@/lib";
import InsightsContextProvider from "@/context/InsightsContextProvider";
import InsightsShell from "./InsightsShell";

/**
 * Server component so it can read the session directly — the same shape
 * app/layout.js uses to hand `session` to AppShell. `UserContextProvider` is
 * not mounted on this public route, so `useUserContext()` is not an option
 * here; only "is there a session at all" is needed, never the role.
 */
const DetailedInsightsLayout = async ({ children }) => {
  const session = await auth.getSession();

  return (
    <div className="w-full">
      <InsightsContextProvider>
        <InsightsShell isSignedIn={Boolean(session)}>{children}</InsightsShell>
      </InsightsContextProvider>
    </div>
  );
};

export default DetailedInsightsLayout;
