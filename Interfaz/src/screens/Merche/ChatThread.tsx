import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { Icon } from "../../components/Icon";
import type { MensajeChat, Plan, Receta } from "../../data/types";
import { capitalizar, formatPrecio } from "../../lib/formato";
import { costeIngrediente, diasOrdenados, imagenReceta, listaCompra, totalLista } from "../../lib/lista";

const redondear = (eur: number) => Math.round(eur * 100) / 100;

// Same dish can't repeat within a day, so day + recipe id is a stable key.
const claveReceta = (dia: string, recetaId: string) => `${dia}-${recetaId}`;

// State C: conversation with Merche, plus the plan she proposes.
// Each dish in the plan expands in place to show its ingredients, which can be unticked.
export function ChatThread({
  mensajes,
  plan,
  planEn,
  conclusion,
  cargando,
  onAddAll,
}: {
  mensajes: MensajeChat[];
  plan?: Plan;
  planEn?: string; // id of the Merche message that delivered the plan
  conclusion?: string; // Merche's closing line, shown AFTER the plan
  cargando: boolean;
  onAddAll: (ids: string[]) => void;
}) {
  const finRef = useRef<HTMLDivElement>(null);
  // Ticked producto ids per dish. A dish with no entry has everything ticked.
  const [selecciones, setSelecciones] = useState<Record<string, Set<string>>>({});
  // Dishes whose ingredients are showing.
  const [abiertos, setAbiertos] = useState<Set<string>>(new Set());

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensajes.length, cargando, plan, conclusion]);

  // A new plan starts clean.
  useEffect(() => {
    setSelecciones({});
    setAbiertos(new Set());
  }, [plan?.id]);

  const seleccionDe = (clave: string, receta: Receta): Set<string> =>
    selecciones[clave] ?? new Set(receta.ingredientes.map((i) => i.producto.id));

  const toggleAbierto = (clave: string) =>
    setAbiertos((prev) => {
      const next = new Set(prev);
      if (next.has(clave)) next.delete(clave);
      else next.add(clave);
      return next;
    });

  function toggleIngrediente(clave: string, receta: Receta, productoId: string) {
    setSelecciones((prev) => {
      const next = new Set(prev[clave] ?? seleccionDe(clave, receta));
      if (next.has(productoId)) next.delete(productoId);
      else next.add(productoId);
      return { ...prev, [clave]: next };
    });
  }

  // Whole dish on/off: all ticked -> untick everything, otherwise tick everything.
  function toggleReceta(clave: string, receta: Receta) {
    const todos = seleccionDe(clave, receta).size === receta.ingredientes.length;
    setSelecciones((prev) => ({
      ...prev,
      [clave]: new Set(todos ? [] : receta.ingredientes.map((i) => i.producto.id)),
    }));
  }

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

  // The plan card sits right after the Merche message that delivered it.
  const tarjetaPlan = plan && (
        <div className="mt-5">
          <div className="rounded-[24px] border border-black/6 bg-white p-4 shadow-[0_8px_30px_rgba(28,52,42,0.07)] sm:p-5">
            <h3 className="text-[17px] font-bold">Tu plan</h3>
            <ul className="mt-2 divide-y divide-black/6">
              {diasOrdenados(plan).flatMap(([dia, recetas]) =>
                recetas.map((receta) => {
                  const clave = claveReceta(dia, receta.id);
                  const abierto = abiertos.has(clave);
                  const seleccion = seleccionDe(clave, receta);
                  const marcados = seleccion.size;
                  const total = receta.ingredientes.length;
                  return (
                    <li key={clave}>
                      <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        aria-label={`Incluir ${receta.nombre} en la lista`}
                        checked={marcados === total}
                        ref={(el) => {
                          if (el) el.indeterminate = marcados > 0 && marcados < total;
                        }}
                        onChange={() => toggleReceta(clave, receta)}
                        className="h-5 w-5 shrink-0 accent-brand"
                      />
                      <button
                        type="button"
                        aria-expanded={abierto}
                        aria-controls={`ingredientes-${clave}`}
                        onClick={() => toggleAbierto(clave)}
                        className={`flex min-w-0 flex-1 items-center gap-3 py-3 text-left transition-opacity ${
                          marcados === 0 ? "opacity-50" : ""
                        }`}
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
                        <strong className="text-[15px]">{formatPrecio(precioReceta(clave, receta))}</strong>
                        <span
                          aria-hidden
                          className={`text-xl text-[#7b8781] transition-transform duration-200 ${abierto ? "rotate-90" : ""}`}
                        >
                          ›
                        </span>
                      </button>
                      </div>

                      {/* grid-rows 0fr -> 1fr animates the height without measuring it. */}
                      <div
                        id={`ingredientes-${clave}`}
                        inert={!abierto}
                        className={`grid transition-[grid-template-rows] duration-200 ${
                          abierto ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                        }`}
                      >
                        <ul className="overflow-hidden">
                          {receta.ingredientes.map((ing) => {
                            const marcado = seleccion.has(ing.producto.id);
                            return (
                              <li key={ing.producto.id}>
                                <label className="flex cursor-pointer items-center gap-3 py-2.5 pl-8">
                                  <input
                                    type="checkbox"
                                    checked={marcado}
                                    onChange={() => toggleIngrediente(clave, receta, ing.producto.id)}
                                    className="h-5 w-5 shrink-0 accent-brand"
                                  />
                                  <span
                                    className={`min-w-0 flex-1 truncate text-[15px] font-semibold ${
                                      marcado ? "" : "text-[#7b8781] line-through"
                                    }`}
                                  >
                                    {ing.producto.nombre}
                                  </span>
                                  <span className="text-[15px] text-[#4d5b54]">
                                    {formatPrecio(costeIngrediente(ing))}
                                  </span>
                                </label>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    </li>
                  );
                }),
              )}
            </ul>
            <p className="mt-2 flex items-center justify-between border-t border-black/6 pt-3 text-[15px]">
              <span className="font-semibold text-[#4d5b54]">Total</span>
              <strong className="text-lg">{formatPrecio(totalLista(lineas))}</strong>
            </p>
          </div>

          <div className="mt-4 flex flex-wrap gap-2.5">
            <button
              type="button"
              onClick={() => onAddAll(lineas.map((l) => l.producto.id))}
              className="flex h-12 flex-1 items-center justify-center gap-2 rounded-full bg-brand px-5 text-sm font-bold text-white transition hover:bg-brand-hover sm:flex-none"
            >
              <Icon name="plus" size={20} />
              Añadir en una nueva lista
            </button>
          </div>
        </div>
  );
  const planEnLista = mensajes.some((m) => m.id === planEn);

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
            <Fragment key={m.id}>
              <MensajeMerche>{m.texto}</MensajeMerche>
              {m.id === planEn && tarjetaPlan}
            </Fragment>
          ),
        )}
        {cargando && (
          <MensajeMerche>
            <span className="text-[#7b8781]">Merche está pensando…</span>
          </MensajeMerche>
        )}
        {!planEnLista && tarjetaPlan}
      </div>

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
