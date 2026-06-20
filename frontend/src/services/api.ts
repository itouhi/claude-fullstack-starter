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
