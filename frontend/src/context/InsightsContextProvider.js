"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  useCallback,
} from "react";
import { api } from "@/lib/api";

// Owns the Detailed insights shell state: the selected administration id and
// the record it resolves to (name/region/zone). Lives at the layout level so
// the selection persists while the user switches between tab routes.
//
// The id is the source of truth — it is what the dropdown sets and what every
// tab fetches with. Name, region and zone are derived from it. The reverse
// (holding the name and looking the id up by case-insensitive string match)
// worked, but made the display label the key: an extra lookup on every render,
// and two Tinkhundla sharing a name would have collided.
const InsightsContext = createContext(null);

const InsightsContextProvider = ({ children }) => {
  const [administrationId, setAdministrationId] = useState(null);
  const [administrations, setAdministrations] = useState([]);

  const fetchAdmins = useCallback(async () => {
    try {
      const res = await api("GET", "/iks/administrations");
      console.log("Fetched administrations:", res);
      if (res && Array.isArray(res)) {
        setAdministrations(res);
        // Default to the first inkhundla once the list loads, rather than
        // hardcoding an id. The empty state (Figma 4159:184659) shows only
        // for the brief window before this resolves. Guarded so a user who
        // clears the dropdown before the fetch returns is not overridden.
        setAdministrationId(
          (current) => current ?? (res.length ? res[0].id : null),
        );
      }
    } catch (err) {
      console.error("Failed to fetch administrations:", err);
    }
  }, []);

  useEffect(() => {
    fetchAdmins();
  }, [fetchAdmins]);

  const value = useMemo(() => {
    // No selection, or the list has not loaded yet -> undefined, no guard
    // needed: nothing is dereferenced until a record is actually found.
    const currentAdmin =
      administrations.find((a) => a.id === administrationId) ?? null;
    return {
      administrationId,
      setAdministrationId,
      administrations,
      selectedInkhundla: currentAdmin?.name ?? null,
      region: currentAdmin?.region ?? "",
      zone: currentAdmin?.zone ?? "",
    };
  }, [administrationId, administrations]);

  return (
    <InsightsContext.Provider value={value}>
      {children}
    </InsightsContext.Provider>
  );
};

export const useInsights = () => useContext(InsightsContext);

export default InsightsContextProvider;
