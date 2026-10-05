export const formatPrecio = (eur: number) =>
  eur.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

export const capitalizar = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

// "500 g", "1 l"; empty when the backend sends no size.
export const formatTamano = (tamano?: number, formato?: string) =>
  tamano == null ? "" : `${tamano.toLocaleString("es-ES")} ${formato ?? ""}`.trim();
