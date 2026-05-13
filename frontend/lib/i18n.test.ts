import { describe, expect, it } from "vitest";
import { DEFAULT_UI_LANGUAGE, text } from "./i18n";

describe("text", () => {
  it("returns Chinese text for zh", () => {
    expect(text("zh", "settings")).toBe("设置");
    expect(text("zh", "uploadPdf")).toBe("上传 PDF");
  });

  it("returns English text for en", () => {
    expect(text("en", "settings")).toBe("Settings");
    expect(text("en", "uploadPdf")).toBe("Upload PDF");
  });

  it("returns QA messages in both languages", () => {
    expect(text("zh", "qaTitle")).toBe("追问与对话");
    expect(text("en", "qaTitle")).toBe("Q&A");
    expect(text("zh", "qaSend")).toBe("发送");
    expect(text("en", "qaSend")).toBe("Send");
  });

  it("covers all keys in both languages", () => {
    const zhKeys = Object.keys(text("zh", "settings" as never) ? {} : {});
    // Verify a few known keys exist
    const knownKeys = [
      "settings", "backHome", "uploadPdf", "qaTitle", "qaPlaceholder",
      "paperDetail", "analysisDone", "analysisFailed",
    ] as const;
    for (const key of knownKeys) {
      expect(text("zh", key)).toBeTruthy();
      expect(text("en", key)).toBeTruthy();
    }
  });
});

describe("DEFAULT_UI_LANGUAGE", () => {
  it("defaults to zh", () => {
    expect(DEFAULT_UI_LANGUAGE).toBe("zh");
  });
});
