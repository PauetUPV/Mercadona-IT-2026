// Shopping list maths from docs/contrato.md. The backend sends no totals:
// everything is computed here so it can be recalculated the moment the user
// unticks a day or removes a product.
import { DIAS, type Dia, type Ingrediente, type Plan, type Producto, type Receta } from "../data/types";

export interface LineaCompra {
  producto: Producto;
  unidades: number; // summed fractions, e.g. 0.25 + 0.25
  envases: number; // whole packs to buy
  subtotal: number; // EUR
}

// Tolerance so 2.0000000001 doesn't become 3.
export const envases = (unidades: number) => Math.ceil(unidades - 1e-9);

const redondear = (eur: number) => Math.round(eur * 100) / 100;

// Every ingredient and extra in the plan, merged by product.
export function listaCompra(plan: Plan): LineaCompra[] {
  const porId = new Map<string, { producto: Producto; unidades: number }>();
  const sumar = ({ unidades, producto }: Ingrediente) => {
    const linea = porId.get(producto.id);
    if (linea) linea.unidades += unidades;
    else porId.set(producto.id, { producto, unidades });
  };
  recetasDelPlan(plan).forEach((r) => r.ingredientes.forEach(sumar));
  plan.extras.forEach(sumar);

  return [...porId.values()].map(({ producto, unidades }) => {
    const n = envases(unidades);
    return { producto, unidades, envases: n, subtotal: redondear(n * producto.precio) };
  });
}

export const totalLista = (lineas: LineaCompra[]) =>
  redondear(lineas.reduce((acc, l) => acc + l.subtotal, 0));

export const recetasDelPlan = (plan: Plan): Receta[] => Object.values(plan.dias).flat();

// Week order, not JSON key order. Days with no recipes are dropped.
export function diasOrdenados(plan: Plan): [Dia, Receta[]][] {
  return DIAS.flatMap((dia) => {
    const recetas = plan.dias[dia];
    return recetas && recetas.length > 0 ? [[dia, recetas] as [Dia, Receta[]]] : [];
  });
}

// Recipes have no image of their own: use the first ingredient's thumbnail.
export const imagenReceta = (receta: Receta) => receta.ingredientes[0]?.producto.thumbnail;
