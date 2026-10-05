// The ONLY door to data. Screens import from here, never from fake.ts or fetch.
// Everything is async so a real network call can replace the body later
// without touching any screen.
import { bienvenida, catalogo, planEjemplo, recetas } from "./fake";
import type { MensajeChat, Plan, Producto, Receta, RespuestaChat } from "./types";

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
let n = 0;
const uid = () => `m${++n}`;
const normalizar = (s: string) =>
  s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

// Classic search: "tomate" -> every product that mentions tomate.
export async function buscarProductos(consulta: string): Promise<Producto[]> {
  await wait(400);
  const palabras = normalizar(consulta).split(/\s+/).filter(Boolean);
  return catalogo.filter((prod) => {
    const texto = normalizar(`${prod.nombre} ${prod.detalle}`);
    return palabras.every((palabra) => texto.includes(palabra));
  });
}

export async function getBienvenida(): Promise<MensajeChat> {
  return { id: uid(), autor: "merche", texto: bienvenida };
}

// "comidas de lunes a jueves para 4, 90 €, el martes no cocino"
export async function enviarMensaje(_texto: string): Promise<RespuestaChat> {
  await wait(800);
  return {
    mensaje: {
      id: uid(),
      autor: "merche",
      texto: "¡Listo! Te he preparado el plan de la semana. Cambia lo que no te guste.",
    },
    plan: planEjemplo,
  };
}

export async function cambiarPlato(_dia: string, actualId: string): Promise<Receta> {
  await wait(500);
  const otras = recetas.filter((r) => r.id !== actualId);
  return otras[Math.floor(Math.random() * otras.length)];
}

export async function valorar(_recetaId: string, _meGusto: boolean): Promise<void> {
  await wait(200);
}

export async function crearCarrito(plan: Plan): Promise<{ productos: number; total: number }> {
  await wait(500);
  const productos = plan.dias.reduce((acc, d) => acc + d.receta.ingredientes.length, 0);
  return { productos, total: plan.total };
}
