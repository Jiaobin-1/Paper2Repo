import { afterEach, describe, expect, it, vi } from "vitest";
import { askQuestionStream } from "./api";
import { requestJson } from "./api/client";

function streamFrom(text: string): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text));
      controller.close();
    },
  });
}

describe("askQuestionStream", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("parses token, error, and done SSE events", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          streamFrom(
            [
              'data: {"type":"token","content":"hello"}',
              "",
              'data: {"type":"error","content":"failed"}',
              "",
              'data: {"type":"done","message_id":"msg-1"}',
              "",
            ].join("\n"),
          ),
          { status: 200 },
        ),
      ),
    );

    const events = [];
    for await (const event of askQuestionStream("run-1", "question")) {
      events.push(event);
    }

    expect(events).toEqual([
      { type: "token", content: "hello" },
      { type: "error", content: "failed" },
      { type: "done", message_id: "msg-1" },
    ]);
  });

  it("passes abort signals to fetch", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(streamFrom(""), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    for await (const _event of askQuestionStream("run-1", "question", controller.signal)) {
      // consume stream
    }

    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ signal: controller.signal }),
    );
  });
});

describe("requestJson", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses the fallback message for non-JSON error responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("server error", { status: 500 })));

    await expect(requestJson("/api/fail", {}, "Stable fallback")).rejects.toThrow("Stable fallback");
  });

  it("normalizes network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));

    await expect(requestJson("/api/fail")).rejects.toThrow("网络连接失败，请检查后端服务。");
  });

  it("preserves abort errors", async () => {
    const abortError = new DOMException("Aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abortError));

    await expect(requestJson("/api/fail")).rejects.toBe(abortError);
  });
});
