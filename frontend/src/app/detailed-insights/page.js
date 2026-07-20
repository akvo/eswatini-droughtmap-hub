import { redirect } from "next/navigation";

// /detailed-insights has no content of its own — send it to the default tab.
const DetailedInsightsPage = () => {
  // CDI Explorer is the design's default tab (Figma 4159:184659).
  redirect("/detailed-insights/cdi");
};

export default DetailedInsightsPage;
