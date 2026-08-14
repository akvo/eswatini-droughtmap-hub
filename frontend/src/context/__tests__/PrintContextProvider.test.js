import { useEffect } from "react";
import { render, screen, act, waitFor } from "@testing-library/react";
import PrintContextProvider, { usePrintContext } from "../PrintContextProvider";

// Stands in for a section that has async work to do before it can be printed.
// Registers at mount, exactly as DroughtMapSection does.
const Section = ({ sectionKey = "map", expose }) => {
  const { printMode, registerSection, reportReady } = usePrintContext();
  useEffect(() => registerSection(sectionKey), [registerSection, sectionKey]);
  expose?.(() => reportReady(sectionKey));
  return (
    <div data-testid="section">{printMode ? "expanded" : "collapsed"}</div>
  );
};

const Button = ({ onSettled }) => {
  const { expandForPrint, collapse } = usePrintContext();
  return (
    <>
      <button onClick={() => expandForPrint().then(onSettled)}>expand</button>
      <button onClick={collapse}>collapse</button>
    </>
  );
};

describe("PrintContextProvider (INS-PDF-1 D-9)", () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it("resolves immediately when no section needs to load", async () => {
    const settled = jest.fn();
    render(
      <PrintContextProvider>
        <Button onSettled={settled} />
      </PrintContextProvider>,
    );

    await act(async () => {
      screen.getByText("expand").click();
      jest.advanceTimersByTime(1);
    });

    expect(settled).toHaveBeenCalled();
  });

  it("waits for a registered section, then resolves when it reports ready", async () => {
    const settled = jest.fn();
    let reportReady;
    render(
      <PrintContextProvider>
        <Button onSettled={settled} />
        <Section
          expose={(fn) => {
            reportReady = fn;
          }}
        />
      </PrintContextProvider>,
    );

    await act(async () => {
      screen.getByText("expand").click();
      jest.advanceTimersByTime(1);
    });

    expect(screen.getByTestId("section")).toHaveTextContent("expanded");
    // This is the regression that mattered: an earlier version resolved on a
    // 0ms timer and printed before the section had built anything.
    expect(settled).not.toHaveBeenCalled();

    await act(async () => {
      reportReady();
    });

    await waitFor(() => expect(settled).toHaveBeenCalled());
  });

  it("gives up after the timeout so a silent section cannot strand the button", async () => {
    const settled = jest.fn();
    render(
      <PrintContextProvider>
        <Button onSettled={settled} />
        <Section sectionKey="never-reports" />
      </PrintContextProvider>,
    );

    await act(async () => {
      screen.getByText("expand").click();
      jest.advanceTimersByTime(1);
    });
    expect(settled).not.toHaveBeenCalled();

    await act(async () => {
      jest.advanceTimersByTime(15000);
    });

    await waitFor(() => expect(settled).toHaveBeenCalled());
  });

  it("collapse turns printMode back off", async () => {
    render(
      <PrintContextProvider>
        <Button onSettled={jest.fn()} />
        <Section />
      </PrintContextProvider>,
    );

    await act(async () => {
      screen.getByText("expand").click();
      jest.advanceTimersByTime(1);
    });
    expect(screen.getByTestId("section")).toHaveTextContent("expanded");

    await act(async () => {
      screen.getByText("collapse").click();
    });
    expect(screen.getByTestId("section")).toHaveTextContent("collapsed");
  });
});
