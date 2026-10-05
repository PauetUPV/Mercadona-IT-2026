// Stand-in for the backend. It answers like the real API (docs/contrato.md v3):
// same paths, same JSON, real `Response` objects. service.ts can't tell the
// difference, so switching to the real server is just setting VITE_API_URL.
// Simplifications: budget is ignored and the intent parsing is a few regexes.
import { DIAS, type ChatRequest, type ChatResponse, type Dia, type Ingrediente, type ListaResponse, type Plan, type Producto, type Receta } from "./types";

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
const id = () => Math.random().toString(36).slice(2, 10);
const normalizar = (s: string) =>
  s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

// ---------- catalog ----------

const img = (photo: string) =>
  `https://images.unsplash.com/${photo}?auto=format&fit=crop&w=700&q=80`;

const p = (
  id: string,
  nombre: string,
  precio: number,
  tamano: number,
  formato_tamano: string,
  categoria: string,
  photo: string,
): Producto => ({
  id,
  nombre,
  precio,
  tamano,
  formato_tamano,
  categoria,
  thumbnail: img(photo),
  url: `https://tienda.mercadona.es/product/${id}`,
});

const spaghetti = p("p1", "Espaguetis Hacendado", 0.95, 500, "g", "Arroz, pasta y legumbres", "photo-1551462147-ff29053bfc14");
const tomate = p("p2", "Tomate frito Hacendado", 1.1, 400, "g", "Aceite, especias y salsas", "photo-1607863680026-e113604ccb17");
const huevos = p("p3", "Huevos camperos Hacendado", 2.65, 12, "ud", "Huevos, leche y mantequilla", "photo-1582722872445-44dc5f7e3c8f");
const panceta = p("p4", "Panceta curada Hacendado", 1.85, 150, "g", "Charcutería y quesos", "photo-1529692236671-f1f6cf9683ba");
const queso = p("p5", "Queso parmesano rallado Hacendado", 1.4, 80, "g", "Charcutería y quesos", "photo-1452195100486-9cc805987862");
const pollo = p("p6", "Pechuga de pollo Hacendado", 4.2, 600, "g", "Carne", "photo-1604503468506-a8da13d82791");
const arroz = p("p7", "Arroz redondo Hacendado", 1.35, 1, "kg", "Arroz, pasta y legumbres", "photo-1536304993881-ff6e9eefa2a6");
const lasana = p("p13", "Lasaña boloñesa Hacendado", 2.75, 400, "g", "Platos preparados", "photo-1574894709920-11b28e7367e3");
const polloAsado = p("p14", "Pollo asado con patatas Hacendado", 4.45, 700, "g", "Platos preparados", "photo-1598103442097-8b74394b95c6");
const leche = p("p15", "Leche entera Hacendado", 0.89, 1, "l", "Huevos, leche y mantequilla", "photo-1563636619-e9143da7973b");

// Only used by search.
const catalogo: Producto[] = [
  spaghetti,
  p("p11", "Macarrones Hacendado", 0.95, 500, "g", "Arroz, pasta y legumbres", "photo-1551462147-ff29053bfc14"),
  p("p12", "Tallarines Hacendado", 1.05, 500, "g", "Arroz, pasta y legumbres", "photo-1551462147-ff29053bfc14"),
  tomate,
  p("p8", "Tomate pera", 1.89, 1, "kg", "Fruta y verdura", "photo-1607863680026-e113604ccb17"),
  p("p9", "Tomate cherry", 1.55, 250, "g", "Fruta y verdura", "photo-1607863680026-e113604ccb17"),
  p("p10", "Tomate triturado Hacendado", 1.25, 800, "g", "Aceite, especias y salsas", "photo-1607863680026-e113604ccb17"),
  huevos, panceta, queso, pollo, arroz, lasana, polloAsado, leche,
];

// ---------- recipes ----------

const ing = (producto: Producto, unidades: number): Ingrediente => ({ unidades, producto });
const precioDe = (ings: Ingrediente[]) =>
  Math.round(ings.reduce((acc, i) => acc + i.unidades * i.producto.precio, 0) * 100) / 100;

const receta = (
  rid: string,
  nombre: string,
  tipo: Receta["tipo"],
  ingredientes: Ingrediente[],
  instrucciones?: string,
): Omit<Receta, "raciones"> => ({
  id: rid,
  nombre,
  tipo,
  momento: "comida",
  ingredientes,
  instrucciones,
  precio_estimado: precioDe(ingredientes),
});

const cocinar = [
  receta("r1", "Espaguetis a la carbonara", "cocinar",
    [ing(spaghetti, 1), ing(huevos, 0.5), ing(panceta, 1), ing(queso, 0.5)],
    "Cuece la pasta. Dora la panceta, mezcla los huevos con el queso y une todo fuera del fuego."),
  receta("r2", "Espaguetis al pomodoro", "cocinar",
    [ing(spaghetti, 1), ing(tomate, 1), ing(queso, 0.25)],
    "Cuece la pasta y caliéntala con el tomate frito. Termina con queso rallado."),
  receta("r3", "Pollo con arroz", "cocinar",
    [ing(pollo, 1), ing(arroz, 0.25), ing(tomate, 0.5)],
    "Sofríe el pollo troceado, añade el tomate y el arroz con agua y cuece 18 minutos."),
];
const listos = [
  receta("l1", "Lasaña boloñesa (lista para comer)", "listo_para_comer", [ing(lasana, 2)]),
  receta("l2", "Pollo asado con patatas (listo para comer)", "listo_para_comer", [ing(polloAsado, 2)]),
];

// ---------- sessions ----------

interface Sesion {
  comensales?: number;
  dias: Dia[];
  noCocina: Dia[];
  plan?: Plan;
  historial: { rol: "usuario" | "asistente"; texto: string }[];
}
const sesiones = new Map<string, Sesion>();

const DIA_RE = DIAS.map(normalizar).join("|");
const diaDe = (token: string) => DIAS.find((d) => normalizar(d) === token)!;

function interpretar(texto: string, s: Sesion) {
  const t = normalizar(texto);
  let cambio = false;

  const personas = t.match(/(?:somos|para)\s+(\d+)|(\d+)\s+personas/);
  if (personas) {
    s.comensales = Number(personas[1] ?? personas[2]);
    cambio = true;
  }
  if (/\d+\s*(€|euros?)/.test(t)) cambio = true; // budget: accepted, not used

  const rango = t.match(new RegExp(`(${DIA_RE})\\s+a\\s+(${DIA_RE})`));
  if (rango) {
    s.dias = DIAS.slice(DIAS.indexOf(diaDe(rango[1])), DIAS.indexOf(diaDe(rango[2])) + 1);
    cambio = true;
  } else if (t.includes("fin de semana")) {
    s.dias = ["sábado", "domingo"];
    cambio = true;
  } else if (t.includes("toda la semana")) {
    s.dias = [...DIAS];
    cambio = true;
  }

  for (const m of t.matchAll(new RegExp(`(${DIA_RE})\\s+no\\s+cocino`, "g"))) {
    s.noCocina.push(diaDe(m[1]));
    cambio = true;
  }

  const cambia = t.match(new RegExp(`cambia\\s+(?:el\\s+)?(${DIA_RE})`));
  const anade = t.match(/anade\s+(.+)/);
  return { cambio, cambiaDia: cambia ? diaDe(cambia[1]) : undefined, anade: anade?.[1] };
}

function generarPlan(s: Sesion): Plan {
  const dias = s.dias.length > 0 ? s.dias : DIAS.slice(0, 5);
  const plan: Plan = { id: id(), dias: {}, extras: [], en_casa: ["sal", "pimienta"] };
  let c = 0;
  let l = 0;
  for (const dia of dias) {
    const base = s.noCocina.includes(dia) ? listos[l++ % listos.length] : cocinar[c++ % cocinar.length];
    plan.dias[dia] = [{ ...base, raciones: s.comensales ?? 2 }];
  }
  return plan;
}

function chat(req: ChatRequest): ChatResponse {
  const session_id = req.session_id ?? id();
  const s = sesiones.get(session_id) ?? { dias: [], noCocina: [], historial: [] };
  sesiones.set(session_id, s);
  s.historial.push({ rol: "usuario", texto: req.mensaje });
  if (req.plan) s.plan = req.plan; // what the user sees wins over what we stored

  const { cambio, cambiaDia, anade } = interpretar(req.mensaje, s);
  const responder = (mensaje: string, plan?: Plan, mensaje_conclusion?: string): ChatResponse => {
    s.historial.push({ rol: "asistente", texto: mensaje });
    if (plan) s.plan = plan;
    return { session_id, mensaje, mensaje_conclusion, plan };
  };

  if (cambiaDia && s.plan?.dias[cambiaDia]) {
    const actual = s.plan.dias[cambiaDia]![0];
    const pool = actual.tipo === "cocinar" ? cocinar : listos;
    const otra = pool.find((r) => r.id !== actual.id) ?? actual;
    const plan: Plan = { ...s.plan, id: id(), dias: { ...s.plan.dias, [cambiaDia]: [{ ...otra, raciones: actual.raciones }] } };
    return responder(`Hecho, he cambiado el ${cambiaDia}.`, plan);
  }

  if (anade && s.plan) {
    const palabra = normalizar(anade).replace(/[^a-z0-9 ]/g, "").trim();
    const producto = catalogo.find((x) => normalizar(x.nombre).includes(palabra));
    if (producto) {
      const plan: Plan = { ...s.plan, id: id(), extras: [...s.plan.extras, ing(producto, 1)] };
      return responder(`Añadido: ${producto.nombre}.`, plan);
    }
    return responder(`No encuentro «${anade}» en el catálogo.`);
  }

  if (s.comensales == null) return responder("¿Para cuántas personas cocinamos?");

  if (cambio) {
    const plan = generarPlan(s);
    return responder(`¡Listo! Plan para ${s.comensales} persona(s).`, plan, "¿Qué opinas?");
  }

  if (/gracias/.test(normalizar(req.mensaje))) return responder("¡De nada! Aquí estoy para lo que necesites."); // no plan: nothing changed

  return responder("Cuéntame qué días quieres planificar y, si quieres, tu presupuesto.");
}

function lista(): ListaResponse {
  return { lista_id: `l_${id()}`, mensaje: "Guardada. Luego te pregunto qué tal salió." };
}

// ---------- the "server" ----------

export async function fakeServer(path: string, init?: RequestInit): Promise<Response> {
  const url = new URL(path, "http://fake");
  const body = init?.body ? JSON.parse(String(init.body)) : undefined;
  const metodo = init?.method ?? "GET";

  if (metodo === "GET" && url.pathname === "/productos") {
    await wait(400);
    const palabras = normalizar(url.searchParams.get("q") ?? "").split(/\s+/).filter(Boolean);
    const limite = Number(url.searchParams.get("limite") ?? 50);
    const hits = catalogo.filter((x) => palabras.every((w) => normalizar(x.nombre).includes(w)));
    return json(hits.slice(0, limite));
  }
  if (metodo === "POST" && url.pathname === "/chat") {
    await wait(800);
    if (!String(body?.mensaje ?? "").trim()) return json({ detail: "mensaje vacío" }, 422);
    return json(chat(body));
  }
  if (metodo === "POST" && url.pathname === "/lista") {
    await wait(300);
    return json(lista());
  }
  return json({ detail: "No encontrado" }, 404);
}
