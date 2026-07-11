import { jsonRequestOptions, requestJson } from "./client";
import type { AppSettings, AppSettingsUpdate, LlmCheck, LlmConfig } from "../types";

export function getLlmConfig(): Promise<LlmConfig> {
  return requestJson<LlmConfig>("/api/llm/config", {}, "模型配置加载失败。");
}

export function updateLlmConfig(defaultModel: string): Promise<LlmConfig> {
  return requestJson<LlmConfig>(
    "/api/llm/config",
    jsonRequestOptions({ default_model: defaultModel }, "PUT"),
    "模型配置更新失败。",
  );
}

export function checkLlmConnection(): Promise<LlmCheck> {
  return requestJson<LlmCheck>("/api/llm/check", { method: "POST" }, "模型连接测试失败。");
}

export function getAppSettings(): Promise<AppSettings> {
  return requestJson<AppSettings>("/api/settings", {}, "设置加载失败。");
}

export function updateAppSettings(payload: AppSettingsUpdate): Promise<AppSettings> {
  return requestJson<AppSettings>("/api/settings", jsonRequestOptions(payload, "PUT"), "设置保存失败。");
}
