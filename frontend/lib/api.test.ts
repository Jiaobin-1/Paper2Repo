import { afterEach, describe, expect, it, vi } from "vitest";
import { askQuestionStream } from "./api";

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
