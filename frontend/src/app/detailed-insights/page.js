import { redirect } from "next/navigation";

// /detailed-insights has no content of its own — send it to the default tab.
const DetailedInsightsPage = () => {
  redirect("/detailed-insights/iks");
};

export default DetailedInsightsPage;
