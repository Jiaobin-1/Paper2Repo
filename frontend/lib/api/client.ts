export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const NETWORK_ERROR_MESSAGE = "网络连接失败，请检查后端服务。";

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export async function requestJson<T>(
  path: string,
  options: RequestInit = {},
  fallbackMessage = "请求失败。",
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(apiUrl(path), options);
  } catch (error) {
    if (isAbortError(error)) {
      throw error;
    }
    throw new Error(NETWORK_ERROR_MESSAGE);
  }

  if (!response.ok) {
    const body = await response.clone().json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? fallbackMessage));
  }

  return response.json();
}

export function jsonRequestOptions(payload: unknown, method: "POST" | "PUT" = "POST"): RequestInit {
  return {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  };
}

export function formatApiError(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg ?? JSON.stringify(item)).join("; ");
  }
  return "请求失败。";
}

export function isAbortError(error: unknown): boolean {
  return (
    error instanceof DOMException && error.name === "AbortError"
  ) || (
    typeof error === "object" &&
    error !== null &&
    "name" in error &&
    error.name === "AbortError"
  );
}
