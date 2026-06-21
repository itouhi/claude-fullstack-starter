const BASE_URL = "/api";

export interface HelloResponse {
  message: string;
}

export async function fetchHello(name: string): Promise<HelloResponse> {
  const url = new URL(`${BASE_URL}/hello`, window.location.origin);
  url.searchParams.set("name", name);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

/** 加算結果のレスポンス。 */
export interface SumResponse {
  result: number;
}

/**
 * 2 つの整数の加算を backend に要求する。
 * @param a 加算する整数 1。
 * @param b 加算する整数 2。
 * @returns result を格納した SumResponse。
 */
export async function fetchSum(a: number, b: number): Promise<SumResponse> {
  const url = new URL(`${BASE_URL}/calc/sum`, window.location.origin);
  url.searchParams.set("a", String(a));
  url.searchParams.set("b", String(b));
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
