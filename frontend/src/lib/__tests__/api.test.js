import { api } from "../api";

jest.mock("../auth", () => ({
  getSession: jest.fn().mockResolvedValue(null),
}));

const respondWith = (status, body) => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  });
};

describe("api error handling", () => {
  it("resolves the parsed body on 2xx", async () => {
    respondWith(200, { data: [1] });
    await expect(api("GET", "/x")).resolves.toEqual({ data: [1] });
  });

  it("rejects on 400 with the DRF field errors flattened", async () => {
    respondWith(400, {
      email: ["A user with this email already exists."],
      administration_id: ["This Inkhundla already has an active observer."],
    });
    await expect(api("POST", "/x", { a: 1 })).rejects.toThrow(
      "A user with this email already exists. " +
        "This Inkhundla already has an active observer.",
    );
  });

  it("rejects on 403 with the detail string", async () => {
    respondWith(403, { detail: "You do not have permission." });
    await expect(api("GET", "/x")).rejects.toThrow(
      "You do not have permission.",
    );
  });

  it("falls back to the status code when the body carries no message", async () => {
    respondWith(500, {});
    await expect(api("GET", "/x")).rejects.toThrow("HTTP 500");
  });
});
