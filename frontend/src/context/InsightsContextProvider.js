"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

// Owns the Detailed insights shell state: the selected inkhundla and the admin
// record it resolves to (id/region/zone). Lives at the layout level so the
// selection persists while the user switches between tab routes.
const InsightsContext = createContext(null);

const InsightsContextProvider = ({ children }) => {
  const [selectedInkhundla, setSelectedInkhundla] = useState("Mhlangatane");
  const [administrations, setAdministrations] = useState([]);

  useEffect(() => {
    const fetchAdmins = async () => {
      try {
        const res = await api("GET", "/iks/administrations");
        if (res && Array.isArray(res)) {
          setAdministrations(res);
        }
      } catch (err) {
        console.error("Failed to fetch administrations:", err);
      }
    };
    fetchAdmins();
  }, []);

  const value = useMemo(() => {
    const currentAdmin = administrations.find(
      (a) => a.name.toLowerCase() === selectedInkhundla.toLowerCase(),
    );
    return {
      selectedInkhundla,
      setSelectedInkhundla,
      administrations,
      administrationId: currentAdmin ? currentAdmin.id : null,
      region: currentAdmin ? currentAdmin.region : "",
      zone: currentAdmin ? currentAdmin.zone : "",
    };
  }, [selectedInkhundla, administrations]);

  return (
    <InsightsContext.Provider value={value}>
      {children}
    </InsightsContext.Provider>
  );
};

export const useInsights = () => useContext(InsightsContext);

export default InsightsContextProvider;
