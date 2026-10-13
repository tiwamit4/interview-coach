import { afterEach, describe, expect, test } from "bun:test";
import {
  api,
  ApiError,
  errorDetail,
  multipart,
  parseQuestions,
  validateFile,
} from "../src/lib/api";
import { toMarkdown } from "../src/components/Results";
const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
});
describe("backend request handling", () => {
  test("returns payloads using the same-origin proxy", async () => {
    let actual = "";
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      actual = String(input);
      return Response.json({ status: "ok" });
    }) as unknown as typeof fetch;
    expect(await api("/health")).toEqual({ status: "ok" });
    expect(actual).toBe("/api/health");
  });
  test("explains field validation and preserves request references", async () => {
    globalThis.fetch = (async () =>
      Response.json(
        {
          detail: [{ loc: ["body", "answer_text"], msg: "Must not be blank" }],
        },
        { status: 422, headers: { "X-Request-ID": "request-123" } },
      )) as unknown as typeof fetch;
    try {
      await api("/sessions/example/answers");
      throw new Error("Expected rejection");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).message).toBe(
        "answer_text: Must not be blank",
      );
      expect((error as ApiError).requestId).toBe("request-123");
    }
  });
  test("handles unavailable backends and non-JSON proxy errors", async () => {
    globalThis.fetch = (async () => {
      throw new TypeError("network");
    }) as unknown as typeof fetch;
    await expect(api("/health")).rejects.toThrow("Cannot reach the backend");
    globalThis.fetch = (async () =>
      new Response("Bad gateway", { status: 502 })) as unknown as typeof fetch;
    await expect(api("/health")).rejects.toThrow("could not be completed");
  });
  test("does not turn cancellation into an error banner", async () => {
    globalThis.fetch = (async () => {
      throw new DOMException("Cancelled", "AbortError");
    }) as unknown as typeof fetch;
    await expect(api("/health")).rejects.toThrow("Cancelled");
  });
});
describe("input and export integrity", () => {
  test("multipart keeps false settings and file contents", () => {
    const file = new File(["resume"], "resume.pdf");
    const form = multipart({
      save_output: false,
      resume: file,
      jd_url: "",
      text: null,
    });
    expect(form.get("save_output")).toBe("false");
    expect((form.get("resume") as File).name).toBe("resume.pdf");
    expect(form.has("jd_url")).toBe(false);
  });
  test("rejects oversized and unsupported resume files", () => {
    expect(() =>
      validateFile(new File(["12345"], "resume.pdf"), 4, "resume"),
    ).toThrow("smaller");
    expect(() =>
      validateFile(new File(["resume"], "resume.txt"), 20, "resume"),
    ).toThrow("PDF");
    expect(() =>
      validateFile(new File(["1234"], "resume.pdf"), 4, "resume"),
    ).not.toThrow();
  });
  test("question imports remove bullets and blank lines", () => {
    expect(
      parseQuestions(
        "1. First question?\n\n- Second question?\n2) Third question?",
      ),
    ).toEqual(["First question?", "Second question?", "Third question?"]);
  });
  test("exports rubric evidence without internal file paths", () => {
    const markdown = toMarkdown({
      output_path: "private/file.json",
      evaluation: {
        score: 90,
        rubric: { depth: { points: 22, quotes: ["I tested the API."] } },
      },
    });
    expect(markdown).toContain("I tested the API.");
    expect(markdown).toContain("22");
    expect(markdown).not.toContain("private/file.json");
  });
  test("unknown errors do not expose raw server responses", () => {
    expect(errorDetail({ secret: "hidden" })).not.toContain("hidden");
  });
});
