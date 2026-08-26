"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { BRIEF_COMPONENT_KEYS } from "@/static/config";

// Owns Brief Builder page state (BB-1, design doc D-3/D-4/D-8).
//
// Two selections, not one. `draft` is what the checkboxes bind to; `applied`
// is what the preview renders and lives in the URL. Apply copies draft ->
// applied. Without that split every tick would fire the preview's fetches,
// which is also why the design has an Apply button at all.
//
// The narrative is deliberately NOT in the URL: free prose would blow past
// practical URL length and leak meeting content into browser history and
// server logs. It lives here only, so a hard refresh returns it to its seeded
// draft — persistence is a Brief model question for the backend round.
const BriefContext = createContext(null);

// A crafted URL must not drive arbitrary requests, so both params are
// validated: the id has to be an integer, and every component key has to be
// one we know about. Unknown keys are dropped silently rather than erroring —
// a stale link from an older catalogue should still render what it can.
const parseComponents = (raw) => {
  const wanted = new Set((raw ?? "").split(",").filter(Boolean));
  return BRIEF_COMPONENT_KEYS.filter((key) => wanted.has(key));
};

const parseInkhundla = (raw) => {
  const id = Number.parseInt(raw ?? "", 10);
  return Number.isInteger(id) && id > 0 ? id : null;
};

// TinyMCE reformats what it is given — it wraps a bare sentence in <p>, and
// emits that as an onEditorChange the moment it mounts. Comparing rendered text
// rather than markup is what stops its own tidy-up from being counted as the
// user typing.
const plainText = (html) =>
  (html ?? "")
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const BriefContextProvider = ({ children }) => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [administrations, setAdministrations] = useState([]);
  // Distinct from `administrations.length`: an empty list that has loaded and
  // one that has not look identical, and they must not — the first means "no
  // such Inkhundla", the second means "wait".
  const [adminsLoaded, setAdminsLoaded] = useState(false);
  const [twg, setTwg] = useState(undefined); // undefined = still loading
  const [narrative, setNarrative] = useState("");
  // Tracks whether the user has touched the narrative, so re-seeding never
  // overwrites their words (D-8).
  const [narrativeEdited, setNarrativeEdited] = useState(false);
  // What the generator last supplied, so an edit can be told from a reformat.
  const seededRef = useRef("");

  // Applied state is read straight off the URL — the page is a function of it.
  const applied = useMemo(
    () => ({
      inkhundla: parseInkhundla(searchParams.get("inkhundla")),
      components: parseComponents(searchParams.get("components")),
    }),
    [searchParams],
  );

  const [draft, setDraft] = useState(applied);

  // A back/forward navigation changes `applied` without going through apply();
  // the checkboxes have to follow, or the panel would show a stale selection.
  useEffect(() => {
    setDraft(applied);
  }, [applied]);

  // A brief describes one Inkhundla. Carrying the previous one's narrative
  // across is not a stale-render nuisance — it would attach prose about Gege to
  // a brief headed Gilgal, and the user could forward it without noticing.
  // Cleared unconditionally, edits included: an edited paragraph is *more*
  // dangerous to carry over, not less.
  useEffect(() => {
    setNarrative("");
    setNarrativeEdited(false);
    seededRef.current = "";
  }, [applied.inkhundla]);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api("GET", "/iks/administrations");
        if (Array.isArray(res)) {
          setAdministrations(res);
        }
      } catch (err) {
        console.error("Failed to fetch administrations:", err);
      } finally {
        // Even on failure: otherwise a dropped request leaves the page
        // spinning on "resolving Inkhundla" with nothing coming.
        setAdminsLoaded(true);
      }
    };
    load();
  }, []);

  // The TWG gate reads /users/me rather than the session cookie: the cookie
  // carries {id, role, abilities, token, expirationTime} and adding a field
  // would leave everyone signed in at deploy time failing the gate until they
  // signed out and back in (D-5). Fails closed — null until proven otherwise.
  useEffect(() => {
    const load = async () => {
      try {
        const res = await api("GET", "/users/me");
        setTwg(res?.technical_working_group ?? null);
      } catch (err) {
        console.error("Failed to resolve TWG membership:", err);
        setTwg(null);
      }
    };
    load();
  }, []);

  const apply = useCallback(() => {
    const params = new URLSearchParams();
    if (draft.inkhundla) {
      params.set("inkhundla", String(draft.inkhundla));
    }
    if (draft.components.length) {
      params.set("components", draft.components.join(","));
    }
    const query = params.toString();
    // replace, not push: Apply refines the current view rather than being a
    // separate destination, so Back should leave the page.
    router.replace(query ? `${pathname}?${query}` : pathname, {
      scroll: false,
    });
  }, [draft, pathname, router]);

  const clearAll = useCallback(() => {
    setDraft({ inkhundla: null, components: [] });
    setNarrative("");
    setNarrativeEdited(false);
    router.replace(pathname, { scroll: false });
  }, [pathname, router]);

  const value = useMemo(() => {
    const record =
      administrations.find((a) => a.id === applied.inkhundla) ?? null;
    // Nothing to apply when the draft already matches what is rendered.
    const isDirty =
      draft.inkhundla !== applied.inkhundla ||
      draft.components.join(",") !== applied.components.join(",");

    // An id off the URL is untrusted input. It is only a real Inkhundla once
    // it matches a row in the fetched list, and no request may be built from
    // it before then — a hand-edited `?inkhundla=5926129` would otherwise fire
    // three 404s and leave the page mid-load with a raw number in the select.
    const resolving = applied.inkhundla != null && !adminsLoaded;
    const unknown = applied.inkhundla != null && adminsLoaded && !record;

    return {
      administrations,
      adminsLoaded,
      applied,
      draft,
      setDraft,
      apply,
      clearAll,
      isDirty,
      inkhundlaResolving: resolving,
      inkhundlaUnknown: unknown,
      // Deliberately null until the id is verified: this is what every fetch
      // keys off, so validation happens once here rather than in each caller.
      administrationId: record?.id ?? null,
      selectedInkhundla: record?.name ?? null,
      region: record?.region ?? "",
      zone: record?.zone ?? "",
      isTwgMember: twg != null,
      twgLoading: twg === undefined,
      narrative,
      narrativeEdited,
      setNarrative: (text) => {
        setNarrative(text);
        // Only a change to the words counts. Without this, TinyMCE's mount-time
        // <p> wrap marks the draft as user-written, which both hides the
        // "Suggested draft" tag and freezes the text against any later reseed.
        if (plainText(text) !== plainText(seededRef.current)) {
          setNarrativeEdited(true);
        }
      },
      // Seeding path — only ever fills an untouched editor.
      seedNarrative: (text) => {
        if (narrativeEdited) {
          return;
        }
        seededRef.current = text;
        setNarrative(text);
      },
    };
  }, [
    administrations,
    adminsLoaded,
    applied,
    draft,
    apply,
    clearAll,
    twg,
    narrative,
    narrativeEdited,
  ]);

  return (
    <BriefContext.Provider value={value}>{children}</BriefContext.Provider>
  );
};

export const useBrief = () => useContext(BriefContext);

export default BriefContextProvider;
