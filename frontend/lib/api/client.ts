export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const NETWORK_ERROR_MESSAGE = "网络连接失败，请检查后端服务。";

export class ApiError extends Error {
  status: number;
  retryAfterSeconds: number | null;

  constructor(message: string, status: number, retryAfterSeconds: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

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
    throw new ApiError(
      formatApiError(body?.detail ?? fallbackMessage),
      response.status,
      parseRetryAfter(response.headers.get("Retry-After")),
    );
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

export function parseRetryAfter(value: string | null): number | null {
  if (!value) {
    return null;
  }
  const seconds = Number.parseInt(value, 10);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}
