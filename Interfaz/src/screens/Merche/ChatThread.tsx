import { useEffect, useRef, useState, type ReactNode } from "react";
import { Icon } from "../../components/Icon";
import { ProductRow } from "../../components/ProductRow";
import type { MensajeChat, Plan, Receta } from "../../data/types";
import { capitalizar, formatPrecio } from "../../lib/formato";
import { costeIngrediente, diasOrdenados, imagenReceta, listaCompra, totalLista } from "../../lib/lista";
import { PlatoDetalle } from "./PlatoDetalle";

const redondear = (eur: number) => Math.round(eur * 100) / 100;

// Same dish can't repeat within a day, so day + recipe id is a stable key.
const claveReceta = (dia: string, recetaId: string) => `${dia}-${recetaId}`;

// State C: conversation with Merche, plus the plan she proposes.
// Each dish in the plan opens its own view with selectable ingredients.
export function ChatThread({
  mensajes,
  plan,
  conclusion,
  cargando,
  added,
  onToggle,
  onAddAll,
  onNotice,
}: {
  mensajes: MensajeChat[];
  plan?: Plan;
  conclusion?: string; // Merche's closing line, shown AFTER the plan
  cargando: boolean;
  added: string[];
  onToggle: (id: string) => void;
  onAddAll: (ids: string[]) => void;
  onNotice: (texto: string) => void;
}) {
  const finRef = useRef<HTMLDivElement>(null);
  const [platoAbierto, setPlatoAbierto] = useState<string | null>(null);
  // Ticked producto ids per dish. A dish with no entry has everything ticked.
  const [selecciones, setSelecciones] = useState<Record<string, Set<string>>>({});

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensajes.length, cargando, plan, conclusion]);

  // A new plan starts clean.
  useEffect(() => {
    setPlatoAbierto(null);
    setSelecciones({});
  }, [plan?.id]);

  const seleccionDe = (clave: string, receta: Receta): Set<string> =>
    selecciones[clave] ?? new Set(receta.ingredientes.map((i) => i.producto.id));

  // Price of a dish counting only its ticked ingredients.
  const precioReceta = (clave: string, receta: Receta): number => {
    const seleccion = seleccionDe(clave, receta);
    return redondear(
      receta.ingredientes.filter((i) => seleccion.has(i.producto.id)).reduce((acc, i) => acc + costeIngrediente(i), 0),
    );
  };

  // The plan as the user has edited it: unticked ingredients are out of the shopping list and total.
  const planEditado: Plan | undefined = plan && {
    ...plan,
    dias: Object.fromEntries(
      diasOrdenados(plan).map(([dia, recetas]) => [
        dia,
        recetas.map((receta) => {
          const seleccion = seleccionDe(claveReceta(dia, receta.id), receta);
          return { ...receta, ingredientes: receta.ingredientes.filter((i) => seleccion.has(i.producto.id)) };
        }),
      ]),
    ),
  };
  const lineas = planEditado ? listaCompra(planEditado) : [];

  if (plan && platoAbierto !== null) {
    for (const [dia, recetas] of diasOrdenados(plan)) {
      for (const receta of recetas) {
        const clave = claveReceta(dia, receta.id);
        if (clave !== platoAbierto) continue;

        const seleccion = seleccionDe(clave, receta);

        return (
          <PlatoDetalle
            dia={dia}
            receta={receta}
            seleccion={seleccion}
            subtotal={precioReceta(clave, receta)}
            onToggle={(id) =>
              setSelecciones((prev) => {
                const next = new Set(prev[clave] ?? seleccion);
                if (next.has(id)) next.delete(id);
                else next.add(id);
                return { ...prev, [clave]: next };
              })
            }
            onVolver={() => setPlatoAbierto(null)}
          />
        );
      }
    }
  }

  return (
    <section aria-label="Conversación con Merche" className="pt-5">
      <div className="flex flex-col gap-4">
        {mensajes.map((m) =>
          m.autor === "usuario" ? (
            <div key={m.id} className="ml-auto max-w-[650px]">
              <div className="rounded-[25px] rounded-br-[8px] bg-brand px-5 py-4 text-[17px] leading-relaxed text-white shadow-[0_10px_25px_rgba(66,148,100,0.18)] sm:text-lg">
                {m.texto}
              </div>
            </div>
          ) : (
            <MensajeMerche key={m.id}>{m.texto}</MensajeMerche>
          ),
        )}
        {cargando && (
          <MensajeMerche>
            <span className="text-[#7b8781]">Merche está pensando…</span>
          </MensajeMerche>
        )}
      </div>

      {plan && (
        <div className="mt-5">
          <div className="rounded-[24px] border border-black/6 bg-white p-4 shadow-[0_8px_30px_rgba(28,52,42,0.07)] sm:p-5">
            <h3 className="text-[17px] font-bold">Tu plan</h3>
            <ul className="mt-2 divide-y divide-black/6">
              {diasOrdenados(plan).flatMap(([dia, recetas]) =>
                recetas.map((receta) => (
                  <li key={claveReceta(dia, receta.id)}>
                    <button
                      type="button"
                      onClick={() => setPlatoAbierto(claveReceta(dia, receta.id))}
                      className="flex w-full items-center gap-3 py-3 text-left transition hover:bg-brand-wash"
                    >
                      <div className="h-14 w-14 shrink-0 overflow-hidden rounded-[14px] bg-[#f4eee1]">
                        <img
                          className="h-full w-full object-cover"
                          src={imagenReceta(receta)}
                          alt=""
                          loading="lazy"
                          onError={(event) => (event.currentTarget.style.visibility = "hidden")}
                        />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-[#7b8781]">
                          {capitalizar(dia)}
                        </p>
                        <p className="truncate text-[15px] font-bold">{receta.nombre}</p>
                      </div>
                      <strong className="text-[15px]">{formatPrecio(precioReceta(claveReceta(dia, receta.id), receta))}</strong>
                      <span aria-hidden className="text-xl text-[#7b8781]">
                        ›
                      </span>
                    </button>
                  </li>
                )),
              )}
            </ul>
            <p className="mt-2 flex items-center justify-between border-t border-black/6 pt-3 text-[15px]">
              <span className="font-semibold text-[#4d5b54]">Total</span>
              <strong className="text-lg">{formatPrecio(totalLista(lineas))}</strong>
            </p>
          </div>

          {lineas.length > 0 && (
            <>
              <h3 className="mt-6 text-lg font-bold">Ingredientes</h3>
              <div className="mt-1 divide-y divide-black/6">
                {lineas.map(({ producto }) => (
                  <ProductRow
                    key={producto.id}
                    producto={producto}
                    added={added.includes(producto.id)}
                    onToggle={() => onToggle(producto.id)}
                  />
                ))}
              </div>
            </>
          )}

          <div className="mt-4 flex flex-wrap gap-2.5">
            <button
              type="button"
              onClick={() => onAddAll(lineas.map((l) => l.producto.id))}
              className="flex h-12 flex-1 items-center justify-center gap-2 rounded-full border-[1.5px] border-brand px-5 text-sm font-bold text-brand transition hover:bg-brand-wash sm:flex-none"
            >
              <Icon name="list" size={20} />
              Añadir todo
            </button>
            <button
              type="button"
              onClick={() => onNotice("Buscando otra receta para ti…")}
              className="flex h-12 flex-1 items-center justify-center gap-2 rounded-full border-[1.5px] border-brand px-5 text-sm font-bold text-brand transition hover:bg-brand-wash sm:flex-none"
            >
              <Icon name="chef" size={20} />
              Ver otra receta
            </button>
          </div>
        </div>
      )}
      {conclusion && !cargando && (
        <div className="mt-4">
          <MensajeMerche>{conclusion}</MensajeMerche>
        </div>
      )}
      <div ref={finRef} />
    </section>
  );
}

function MensajeMerche({ children }: { children: ReactNode }) {
  return (
    <div className="flex max-w-[720px] items-start gap-3">
      <div className="mt-1 grid h-11 w-11 shrink-0 place-items-center rounded-[15px] bg-brand text-white shadow-[0_7px_18px_rgba(66,148,100,0.2)]">
        <Icon name="chef" size={23} strokeWidth={2.2} />
      </div>
      <div>
        <div className="rounded-[25px] rounded-tl-[8px] bg-[#f0f3f1] px-5 py-4 text-[17px] leading-relaxed sm:text-lg">
          {children}
        </div>
        <p className="ml-2 mt-1.5 text-xs font-medium text-[#7b8781]">Merche</p>
      </div>
    </div>
  );
}
