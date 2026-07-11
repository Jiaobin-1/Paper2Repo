import { describe, expect, it } from "vitest";
import { batchCompletionMessage } from "./batchPresentation";

describe("batchCompletionMessage", () => {
  it("uses the completed message when every run completed", () => {
    expect(batchCompletionMessage([true, true], "en")).toBe("Batch analysis complete.");
  });

  it("uses the partial failure message when any run failed", () => {
    expect(batchCompletionMessage([true, false], "en")).toBe("Batch analysis finished with some failures.");
  });
});
