// Data shapes = docs/contrato.md (v3), field names exactly as on the wire.
// No mapping layer: what the backend sends is what the screens read.

// Where a query from the Merche bar goes: classic product search or the bot.
export type Intencion = "buscar" | "merche";

// Always lowercase with accents, as the contract says. Order = week order.
export const DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"] as const;
export type Dia = (typeof DIAS)[number];

export type TipoPlato = "cocinar" | "listo_para_comer";

export interface Producto {
  id: string;
  nombre: string;
  precio: number; // EUR, ONE pack
  precio_referencia?: number;
  formato_referencia?: string; // "L", "kg"
  tamano?: number;
  formato_tamano?: string; // "l", "g"
  categoria?: string;
  subcategoria?: string;
  thumbnail?: string;
  url?: string;
}

export interface Ingrediente {
  unidades: number; // may be a fraction of a pack (0.25). See lib/lista.ts
  producto: Producto;
}

export interface Receta {
  id: string;
  nombre: string;
  tipo: TipoPlato; // listo_para_comer = exactly one ingredient: the product itself
  momento?: "comida" | "cena"; // ignored for now
  raciones: number;
  ingredientes: Ingrediente[];
  instrucciones?: string;
  precio_estimado: number;
  en_casa?: string[];
}

export interface Plan {
  id: string; // changes whenever the content changes
  dias: Partial<Record<Dia, Receta[]>>;
  extras: Ingrediente[]; // buyable things that belong to no recipe (milk, coffee)
  en_casa: string[]; // assumed at home (salt, water): text only, not priced
}

// POST /chat
export interface ChatRequest {
  session_id?: string;
  mensaje: string;
  plan?: Plan; // only when the user edited the plan since the last response
}

export interface ChatResponse {
  session_id: string;
  mensaje: string;
  mensaje_conclusion?: string | null; // goes AFTER the plan
  plan?: Plan | null; // absent/null = nothing changed, keep the last one
}

// POST /lista
export interface LineaLista {
  producto_id: string;
  unidades: number; // whole packs, already edited by the user
}

export interface ListaRequest {
  session_id: string;
  plan_id?: string;
  nombre?: string;
  lineas: LineaLista[];
}

export interface ListaResponse {
  lista_id: string;
  mensaje?: string | null; // shown as a Merche bubble
}

// UI-only shapes (not in the contract).
export interface MensajeChat {
  id: string;
  autor: "usuario" | "merche";
  texto: string;
}

export interface RespuestaChat {
  mensaje: string;
  conclusion?: string;
  plan?: Plan;
}
