export const formatPrecio = (eur: number) =>
  eur.toLocaleString("es-ES", { style: "currency", currency: "EUR" });
