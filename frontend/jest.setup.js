import "@testing-library/jest-dom";
// Learn more: https://github.com/testing-library/jest-dom
import { configure } from "@testing-library/react";
import { TextEncoder, TextDecoder } from "util";

// RTL's waitFor/findBy default is 1s. CI runs several jest workers on shared
// CPUs and most suites here mount antd Modals/Drawers, so that budget expires
// on a slow render rather than on anything actually being stuck — the failure
// then reads as a false assertion ("button is disabled") instead of a timeout.
// Kept under jest.config's testTimeout so a genuine hang still fails as one.
configure({ asyncUtilTimeout: 5000 });

// Polyfill for `TextEncoder` and `TextDecoder`
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
