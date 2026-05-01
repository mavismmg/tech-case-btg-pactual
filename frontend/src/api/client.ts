const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "library_api_token";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

type RequestOptions = RequestInit & {
  auth?: boolean;
};

function buildUrl(path: string, params?: Record<string, string | number | boolean | undefined | null>) {
  const url = new URL(path, API_URL);
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });
  return url.toString();
}

async function parseResponse(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function parseApiErrorDetail(body: unknown) {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;

    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === "object" && item !== null && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return String(item);
        })
        .join(" ");
    }

    return String(detail);
  }

  return typeof body === "string" ? body : "";
}

export async function api<T>(
  path: string,
  options: RequestOptions = {},
  params?: Record<string, string | number | boolean | undefined | null>,
): Promise<T> {
  try {
    const headers = new Headers(options.headers);
    const token = getToken();

    if (!headers.has("Content-Type") && options.body) {
      headers.set("Content-Type", "application/json");
    }

    if (options.auth !== false && token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(buildUrl(path, params), {
      ...options,
      headers,
    });
    const body = await parseResponse(response);

    if (!response.ok) {
      throw new ApiError(response.status, parseApiErrorDetail(body) || "Erro inesperado na API.");
    }

    return body as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    throw new TypeError("Não foi possível conectar ao servidor.");
  }
}

export const pageParams = (page: number, limit = 10) => ({
  skip: Math.max(0, page * limit),
  limit,
});
