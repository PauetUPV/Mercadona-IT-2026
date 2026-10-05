// Data shapes the UI needs. Proposed contract for the backend team.

export type TipoPlato = "cocinar" | "listo_para_comer";

export interface Producto {
  id: string;
  nombre: string;
  detalle: string; // "La Molisana · 500 g"
  precio: number; // EUR
  imagen: string;
}

export interface Receta {
  id: string;
  nombre: string;
  tipo: TipoPlato;
  precio: number; // EUR, total for the people in the plan
  imagen: string;
  ingredientes: Producto[];
}

export interface PlanDia {
  dia: string; // "Lunes"
  receta: Receta;
}

export interface Plan {
  comensales: number;
  presupuesto: number | null;
  total: number;
  dias: PlanDia[];
}

export interface MensajeChat {
  id: string;
  autor: "usuario" | "merche";
  texto: string;
}

export interface RespuestaChat {
  mensaje: MensajeChat;
  plan?: Plan; // present when Merche proposes a plan
}
