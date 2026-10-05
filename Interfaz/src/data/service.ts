// The ONLY door to data. Screens import from here, never from fake.ts or fetch.
// Wire format = docs/contrato.md. With VITE_API_URL set it talks to the real
// backend; without it, to the fake one in fake.ts (same paths, same JSON).
import { fakeServer } from "./fake";
import type {
  ChatRequest,
  ChatResponse,
  FeedbackRequest,
  FeedbackResponse,
  LineaLista,
  ListaRequest,
  ListaResponse,
  Plan,
  Producto,
  RespuestaChat,
  SujetoPendiente,
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

// The backend keeps the chat history (and saved lists, ratings...) per session; we only send
// the new message. The id survives reloads, so Merche can later ask how the saved list went.
const CLAVE_SESION = "merche.session_id";
const nuevoId = () => `s${Math.random().toString(36).slice(2, 10)}`;

function leerSesion(): string {
  try {
    return localStorage.getItem(CLAVE_SESION) ?? nuevoId();
  } catch {
    return nuevoId(); // storage blocked: the session just won't survive a reload
  }
}

function recordarSesion(id: string) {
  sessionId = id;
  try {
    localStorage.setItem(CLAVE_SESION, id);
  } catch {
    // storage blocked: nothing to do
  }
}

let sessionId = leerSesion();
// After "Volver", the previous session id is sent once so the backend carries over the user's
// long-term memory (saved lists to ask about, likes and dislikes, diet). The chat itself starts empty.
let sesionAnterior: string | undefined;

// Call when the user starts a conversation from scratch ("Volver"), so the
// backend doesn't carry context the user thinks is gone.
export function nuevaSesion() {
  sesionAnterior = sessionId;
  recordarSesion(nuevoId());
}

// Once the backend has created the new session (and inherited), there is nothing left to pass on.
function heredado() {
  sesionAnterior = undefined;
}

const respuestaChat = (r: ChatResponse): RespuestaChat => ({
  mensaje: r.mensaje,
  conclusion: r.mensaje_conclusion ?? undefined,
  plan: r.plan ?? undefined, // null/absent = nothing changed
  sugerencias: r.sugerencias ?? undefined,
  feedback: r.feedback ?? undefined,
  enviado: r.enviado ?? undefined,
});

// Classic search: "tomate" -> every product that mentions tomate.
export function buscarProductos(consulta: string): Promise<Producto[]> {
  return request<Producto[]>(`/productos?q=${encodeURIComponent(consulta)}&limite=50`);
}

// Merche's opening line when the screen opens: a greeting, or "how did X turn out?" (with `feedback`).
export async function bienvenida(): Promise<RespuestaChat> {
  const anterior = sesionAnterior ? `&sesion_anterior=${encodeURIComponent(sesionAnterior)}` : "";
  const r = await request<ChatResponse>(`/bienvenida?session_id=${encodeURIComponent(sessionId)}${anterior}`);
  recordarSesion(r.session_id);
  heredado();
  return respuestaChat(r);
}

// "comidas de lunes a jueves para 4, 90 €, el martes no cocino"
// Pass `planEditado` only if the user edited the plan since the last response.
export async function enviarMensaje(texto: string, planEditado?: Plan): Promise<RespuestaChat> {
  const peticion: ChatRequest = { session_id: sessionId, mensaje: texto, plan: planEditado, sesion_anterior: sesionAnterior };
  const r = await post<ChatResponse>("/chat", peticion);
  recordarSesion(r.session_id);
  heredado();
  return respuestaChat(r);
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

// Thumbs up/down on something Merche asked about. A thumbs down without `motivo` comes back with
// reason chips; send the chosen one with the same call plus `motivo`.
export function valorar(
  sujeto: SujetoPendiente,
  valor: FeedbackRequest["valor"],
  motivo?: string,
): Promise<FeedbackResponse> {
  const peticion: FeedbackRequest = { session_id: sessionId, sujeto: { tipo: sujeto.tipo, id: sujeto.id }, valor, motivo };
  return post<FeedbackResponse>("/feedback", peticion);
}
