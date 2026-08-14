"use client";

import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";

/**
 * Coordinates the National Overview PDF export (INS-PDF-1 D-9).
 *
 * The download button lives in HeroSection; the content that has to expand for
 * print — every map layer, both zone groupings — lives in sibling sections. The
 * button therefore cannot simply print: it has to ask the sections to expand,
 * wait until they say they are ready, and only then open the print dialog.
 *
 * Contract:
 *   expandForPrint()  button → sections. Flips printMode on and returns a
 *                     promise that settles when every registered section has
 *                     reported ready (or the timeout fires).
 *   collapse()        button → sections. Tears the print-only content back down.
 *   printMode         sections read this to decide whether to render their
 *                     print-only blocks.
 *   registerSection() a section that loads asynchronously calls this ON MOUNT,
 *                     not when printing starts, and gets back an unregister.
 *   reportReady()     that section calls this once its print content is built.
 *
 * Registration deliberately happens at mount rather than in response to
 * printMode. The earlier version registered on expand and asked "has anything
 * registered yet?" on a 0ms timer — a race the button won, so it printed before
 * the maps existed. Participants known up front means the answer is never a
 * guess.
 */
const PrintContext = createContext(null);

export const usePrintContext = () => useContext(PrintContext);

// A section that never reports must not strand the button on a spinner
// forever. 15s is far past the six layer fetches this waits on in practice.
const READY_TIMEOUT_MS = 15000;

const PrintContextProvider = ({ children }) => {
  const [printMode, setPrintMode] = useState(false);
  const participantsRef = useRef(new Set());
  const readyRef = useRef(new Set());
  const resolveRef = useRef(null);
  const timeoutRef = useRef(null);

  const settleIfDone = useCallback(() => {
    if (!resolveRef.current) {
      return;
    }
    const allReady = [...participantsRef.current].every((key) =>
      readyRef.current.has(key),
    );
    if (allReady) {
      clearTimeout(timeoutRef.current);
      resolveRef.current();
      resolveRef.current = null;
    }
  }, []);

  const registerSection = useCallback(
    (key) => {
      participantsRef.current.add(key);
      return () => {
        participantsRef.current.delete(key);
        readyRef.current.delete(key);
        // A section that unmounts mid-print must not hold the promise open.
        settleIfDone();
      };
    },
    [settleIfDone],
  );

  const reportReady = useCallback(
    (key) => {
      readyRef.current.add(key);
      settleIfDone();
    },
    [settleIfDone],
  );

  const expandForPrint = useCallback(() => {
    readyRef.current.clear();
    setPrintMode(true);
    return new Promise((resolve) => {
      resolveRef.current = resolve;
      // Safe to check immediately: participants registered at mount, so an
      // empty set genuinely means there is nothing to wait for.
      if (participantsRef.current.size === 0) {
        resolveRef.current = null;
        resolve();
        return;
      }
      timeoutRef.current = setTimeout(() => {
        resolveRef.current?.();
        resolveRef.current = null;
      }, READY_TIMEOUT_MS);
    });
  }, []);

  const collapse = useCallback(() => {
    clearTimeout(timeoutRef.current);
    readyRef.current.clear();
    resolveRef.current = null;
    setPrintMode(false);
  }, []);

  return (
    <PrintContext.Provider
      value={{
        printMode,
        expandForPrint,
        collapse,
        registerSection,
        reportReady,
      }}
    >
      {children}
    </PrintContext.Provider>
  );
};

export default PrintContextProvider;
