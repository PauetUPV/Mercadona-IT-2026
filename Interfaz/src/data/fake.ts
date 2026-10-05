import type { Plan, Producto, Receta } from "./types";

const img = (id: string) =>
  `https://images.unsplash.com/${id}?auto=format&fit=crop&w=700&q=80`;

const p = (
  id: string,
  nombre: string,
  detalle: string,
  precio: number,
  imagen: string,
): Producto => ({ id, nombre, detalle, precio, imagen });

export const spaghetti = p("p1", "Espaguetis", "Hacendado · 500 g", 0.95, img("photo-1551462147-ff29053bfc14"));
export const tomate = p("p2", "Tomate frito", "Hacendado · 400 g", 1.1, img("photo-1607863680026-e113604ccb17"));
export const huevos = p("p3", "Huevos camperos", "Hacendado · 12 ud", 2.65, img("photo-1582722872445-44dc5f7e3c8f"));
export const panceta = p("p4", "Panceta curada", "Hacendado · 150 g", 1.85, img("photo-1529692236671-f1f6cf9683ba"));
export const queso = p("p5", "Queso parmesano rallado", "Hacendado · 80 g", 1.4, img("photo-1452195100486-9cc805987862"));
export const pollo = p("p6", "Pechuga de pollo", "Hacendado · 600 g", 4.2, img("photo-1604503468506-a8da13d82791"));
export const arroz = p("p7", "Arroz redondo", "Hacendado · 1 kg", 1.35, img("photo-1536304993881-ff6e9eefa2a6"));

const tomatePera = p("p8", "Tomate pera", "Hacendado · 1 kg", 1.89, img("photo-1607863680026-e113604ccb17"));
const tomateCherry = p("p9", "Tomate cherry", "Hacendado · 250 g", 1.55, img("photo-1607863680026-e113604ccb17"));
const tomateTriturado = p("p10", "Tomate triturado", "Hacendado · 800 g", 1.25, img("photo-1607863680026-e113604ccb17"));
const macarrones = p("p11", "Macarrones", "Hacendado · 500 g", 0.95, img("photo-1551462147-ff29053bfc14"));
const tallarines = p("p12", "Tallarines", "Hacendado · 500 g", 1.05, img("photo-1551462147-ff29053bfc14"));

// Everything the fake search can find.
export const catalogo: Producto[] = [
  spaghetti, macarrones, tallarines,
  tomate, tomatePera, tomateCherry, tomateTriturado,
  huevos, panceta, queso, pollo, arroz,
];

export const recetas: Receta[] = [
  {
    id: "r1",
    nombre: "Espaguetis a la carbonara",
    tipo: "cocinar",
    precio: 7.8,
    imagen: img("photo-1612874742237-6526221588e3"),
    ingredientes: [spaghetti, huevos, panceta, queso],
  },
  {
    id: "r2",
    nombre: "Espaguetis al pomodoro",
    tipo: "cocinar",
    precio: 4.4,
    imagen: img("photo-1551462147-ff29053bfc14"),
    ingredientes: [spaghetti, tomate, queso],
  },
  {
    id: "r3",
    nombre: "Pollo con arroz",
    tipo: "cocinar",
    precio: 9.2,
    imagen: img("photo-1604503468506-a8da13d82791"),
    ingredientes: [pollo, arroz, tomate],
  },
  {
    id: "r4",
    nombre: "Lasaña de carne (lista para comer)",
    tipo: "listo_para_comer",
    precio: 6.5,
    imagen: img("photo-1574894709920-11b28e7367e3"),
    ingredientes: [],
  },
  {
    id: "r5",
    nombre: "Pollo asado con patatas (listo para comer)",
    tipo: "listo_para_comer",
    precio: 8.9,
    imagen: img("photo-1598103442097-8b74394b95c6"),
    ingredientes: [],
  },
];

export const planEjemplo: Plan = {
  comensales: 4,
  presupuesto: 90,
  total: 36.3,
  dias: [
    { dia: "Lunes", receta: recetas[0] },
    { dia: "Martes", receta: recetas[3] },
    { dia: "Miércoles", receta: recetas[2] },
    { dia: "Jueves", receta: recetas[1] },
  ],
};

export const bienvenida =
  "¡Hola! Soy Merche. Dime qué días quieres planificar, para cuántos y tu presupuesto.";
