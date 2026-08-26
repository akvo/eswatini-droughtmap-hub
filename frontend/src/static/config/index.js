// Split out of the former single static/config.js (1010 lines).
// Barrel: `@/static/config` keeps working unchanged for every importer.
// Import from a module directly when you only need one group.

export * from "./activity";
export * from "./app";
export * from "./brief";
export * from "./drought";
export * from "./iks";
export * from "./publication";
export * from "./review";
export * from "./sectors";
