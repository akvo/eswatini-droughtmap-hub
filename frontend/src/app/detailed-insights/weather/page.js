"use client";

import { useInsights } from "@/context/InsightsContextProvider";

const WeatherPage = () => {
  const { selectedInkhundla } = useInsights();

  return (
    <div className="p-8 text-center bg-white rounded-b-lg">
      <h3 className="text-lg font-bold text-neutral-800 mb-2">
        Weather Stations Explorer
      </h3>
      <p className="text-neutral-500 max-w-md mx-auto text-sm">
        The Weather Stations tab displays temperature and rainfall aggregates
        for {selectedInkhundla} Inkhundla. This tab is currently under
        construction.
      </p>
    </div>
  );
};

export default WeatherPage;
