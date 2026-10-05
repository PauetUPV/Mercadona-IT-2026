// The ONLY door to data. Screens import from here, never from fake.ts or fetch.
// Wire format = docs/contrato.md. With VITE_API_URL set it talks to the real
// backend; without it, to the fake one in fake.ts (same paths, same JSON).
import { fakeServer } from "./fake";
import type {
  ChatRequest,
  ChatResponse,
  LineaLista,
  ListaRequest,
  ListaResponse,
  Plan,
  Producto,
  RespuestaChat,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL as string | undefined;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const options = { headers: { "Content-Type": "application/json" }, ...init };
  const res = API_URL ? await fetch(API_URL + path, options) : await fakeServer(path, options);
  if (!res.ok) throw new Error(`${options.method ?? "GET"} ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

// The backend keeps the chat history per session; we only send the new message.
const nuevoId = () => `s${Math.random().toString(36).slice(2, 10)}`;
let sessionId = nuevoId();

// Call when the user starts a conversation from scratch ("Volver"), so the
// backend doesn't carry context the user thinks is gone.
export function nuevaSesion() {
  sessionId = nuevoId();
}

// Classic search: "tomate" -> every product that mentions tomate.
export function buscarProductos(consulta: string): Promise<Producto[]> {
  return request<Producto[]>(`/productos?q=${encodeURIComponent(consulta)}&limite=50`);
}

// "comidas de lunes a jueves para 4, 90 €, el martes no cocino"
// Pass `planEditado` only if the user edited the plan since the last response.
export async function enviarMensaje(texto: string, planEditado?: Plan): Promise<RespuestaChat> {
  const peticion: ChatRequest = { session_id: sessionId, mensaje: texto, plan: planEditado };
  const r = await post<ChatResponse>("/chat", peticion);
  sessionId = r.session_id;
  return {
    mensaje: r.mensaje,
    conclusion: r.mensaje_conclusion ?? undefined,
    plan: r.plan ?? undefined, // null/absent = nothing changed
  };
}

// The user reviewed the list and pressed save. Returns Merche's reply, if any.
export async function guardarLista(
  lineas: LineaLista[],
  planId?: string,
  nombre?: string,
): Promise<ListaResponse> {
  const peticion: ListaRequest = { session_id: sessionId, plan_id: planId, nombre, lineas };
  return post<ListaResponse>("/lista", peticion);
}
