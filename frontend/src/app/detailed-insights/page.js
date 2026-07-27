"use client";

import { useInsights } from "@/context/InsightsContextProvider";

// CDI Explorer is the default tab, so it lives at the index route itself
// rather than behind a redirect — a redirect() here would fire during the
// layout's deferred (empty-state) render and corrupt the App Router's hooks.
const CdiPage = () => {
  const { selectedInkhundla } = useInsights();

  return (
    <div className="p-8 text-center bg-white border border-cardBorder border-t-0">
      <h3 className="text-lg font-bold text-neutral-800 mb-2">CDI Explorer</h3>
      <p className="text-neutral-500 max-w-md mx-auto text-sm">
        The CDI Explorer tab provides historical satellite drought category
        trends for {selectedInkhundla} Inkhundla. This tab is currently under
        construction.
      </p>
    </div>
  );
};

export default CdiPage;
