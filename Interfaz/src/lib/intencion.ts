// Decides where a query from the Merche bar goes. The ONLY place that knows
// the rule: swap the body when we want something smarter than word count.
import type { Intencion } from "../data/types";

const MAX_PALABRAS_BUSQUEDA = 3;
const PALABRAS_MERCHE = [
  "menu",
  "receta",
  "recetas",
  "cena",
  "comida",
  "comidas",
  "personas",
  "presupuesto",
  "semana",
];

const normalizar = (s: string) =>
  s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");

export function decidirIntencion(texto: string): Intencion {
  const t = normalizar(texto).trim();
  if (!t) return "buscar";
  if (t.includes("?")) return "merche";
  const palabras = t.split(/\s+/);
  if (palabras.length > MAX_PALABRAS_BUSQUEDA) return "merche";
  return palabras.some((p) => PALABRAS_MERCHE.includes(p)) ? "merche" : "buscar";
}
