export const formatPrecio = (eur: number) =>
  eur.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

export const capitalizar = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

// "500 g", "1 l"; empty when the backend sends no size.
export const formatTamano = (tamano?: number, formato?: string) =>
  tamano == null ? "" : `${tamano.toLocaleString("es-ES")} ${formato ?? ""}`.trim();

// ---- Ingredient quantity -------------------------------------------------
// The backend only says which fraction of a pack a recipe uses (`unidades`), so the
// amount is unidades x tamano, rounded to something a person would measure.

const num = (n: number) => n.toLocaleString("es-ES", { maximumFractionDigits: 2 });
const FRACCIONES: Record<number, string> = { 0.25: "¼", 0.5: "½", 0.75: "¾" };

// Nearest quarter, never zero ("a bit" beats "0"). Text like "¾", "1½", "3".
function aCuartos(n: number) {
  const q = Math.max(0.25, Math.round(n * 4) / 4);
  const entero = Math.floor(q);
  const texto = `${entero > 0 ? entero : ""}${FRACCIONES[q - entero] ?? ""}`;
  return { q, texto, exacto: Math.abs(q - n) < 0.01 };
}

// g / ml, rounded by size: 7 -> 7, 62 -> 60, 167 -> 170, 1330 -> 1350.
const redondearMedida = (n: number) =>
  n < 10 ? Math.max(1, Math.round(n)) : n < 100 ? Math.round(n / 5) * 5 : n < 1000 ? Math.round(n / 10) * 10 : Math.round(n / 50) * 50;

function medida(base: number, pequena: string, grande: string) {
  const r = redondearMedida(base);
  const texto = r >= 1000 ? `${num(r / 1000)} ${grande}` : `${num(r)} ${pequena}`;
  return { texto, exacto: Math.abs(r - base) / base < 0.005 };
}

// "250 ml", "≈ 170 g", "3 uds", "¼ de envase". "≈" when rounding changed the value.
export function formatCantidad(unidades: number, tamano?: number, formato?: string): string {
  const f = formato?.trim().toLowerCase();
  let r: { texto: string; exacto: boolean };

  if (!tamano || !f) {
    const { q, texto, exacto } = aCuartos(unidades);
    r = { texto: q < 1 ? `${texto} de envase` : `${texto} ${q === 1 ? "envase" : "envases"}`, exacto };
  } else {
    const total = unidades * tamano;
    if (f === "kg") r = medida(total * 1000, "g", "kg");
    else if (f === "g") r = medida(total, "g", "kg");
    else if (f === "l") r = medida(total * 1000, "ml", "l");
    else if (f === "ml") r = medida(total, "ml", "l");
    else if (f === "ud") {
      const { q, texto, exacto } = aCuartos(total);
      r = { texto: `${texto} ${q > 1 ? "uds" : "ud"}`, exacto };
    } else {
      const redondeado = Math.round(total * 100) / 100;
      r = { texto: `${num(redondeado)} ${f}`, exacto: Math.abs(redondeado - total) < 1e-9 };
    }
  }
  return r.exacto ? r.texto : `≈ ${r.texto}`;
}
