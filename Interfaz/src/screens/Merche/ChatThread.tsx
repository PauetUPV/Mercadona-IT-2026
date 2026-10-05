import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { Icon } from "../../components/Icon";
import type { LineaLista, MensajeChat, Plan, Receta, SujetoPendiente } from "../../data/types";
import { capitalizar, formatCantidad, formatPrecio } from "../../lib/formato";
import { costeIngrediente, diasOrdenados, imagenReceta, listaCompra, totalLista } from "../../lib/lista";

const redondear = (eur: number) => Math.round(eur * 100) / 100;

// Same dish can't repeat within a day, so day + recipe id is a stable key.
const claveReceta = (dia: string, recetaId: string) => `${dia}-${recetaId}`;

// Quick-reply chips under the last message. With `motivoDe`, they are the reasons for a thumbs down
// on that item (sent to /feedback); otherwise they are messages for Merche (sent to /chat).
export interface Chips {
  textos: string[];
  motivoDe?: SujetoPendiente;
}

// State C: conversation with Merche, plus the plan she proposes.
// Each dish in the plan expands in place to show its ingredients, which can be unticked.
export function ChatThread({
  mensajes,
  plan,
  planEn,
  conclusion,
  chips,
  cargando,
  onAddAll,
  onGuardarLista,
  onPlanEditado,
  onChip,
  onFeedback,
}: {
  mensajes: MensajeChat[];
  plan?: Plan;
  planEn?: string; // id of the Merche message that delivered the plan
  conclusion?: string; // Merche's closing line, shown AFTER the plan
  chips?: Chips;
  cargando: boolean;
  onAddAll: (ids: string[]) => void;
  onGuardarLista: (lineas: LineaLista[], planId?: string) => void;
  onPlanEditado: (plan: Plan | undefined) => void; // the plan as the user edited it, or undefined if untouched
  onChip: (texto: string, chips: Chips) => void;
  onFeedback: (mensajeId: string, sujeto: SujetoPendiente, valor: "positivo" | "negativo") => void;
}) {
  const finRef = useRef<HTMLDivElement>(null);
  // Ticked producto ids per dish. A dish with no entry has everything ticked.
  const [selecciones, setSelecciones] = useState<Record<string, Set<string>>>({});
  // Dishes whose ingredients are showing.
  const [abiertos, setAbiertos] = useState<Set<string>>(new Set());

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensajes.length, cargando, plan, conclusion, chips]);

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

  // Tell the page what the user edited, so the next message sends it (docs/contrato.md "plan en la peticion").
  // Unticked dishes and emptied days leave the plan entirely.
  useEffect(() => {
    if (!plan || Object.keys(selecciones).length === 0) return onPlanEditado(undefined);
    const dias = Object.fromEntries(
      diasOrdenados(plan)
        .map(([dia, recetas]) => [
          dia,
          recetas
            .map((receta) => {
              const seleccion = seleccionDe(claveReceta(dia, receta.id), receta);
              return { ...receta, ingredientes: receta.ingredientes.filter((i) => seleccion.has(i.producto.id)) };
            })
            .filter((receta) => receta.ingredientes.length > 0),
        ] as const)
        .filter(([, recetas]) => recetas.length > 0),
    );
    onPlanEditado({ ...plan, dias });
    // seleccionDe only reads `selecciones`, already a dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selecciones, plan]);

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
                                  <span className="min-w-0 flex-1">
                                    <span
                                      className={`block truncate text-[15px] font-semibold ${
                                        marcado ? "" : "text-[#7b8781] line-through"
                                      }`}
                                    >
                                      {ing.producto.nombre}
                                    </span>
                                    <span className="block text-[13px] text-[#7b8781]">
                                      {formatCantidad(ing.unidades, ing.producto.tamano, ing.producto.formato_tamano)}
                                    </span>
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
              onClick={() => {
                onAddAll(lineas.map((l) => l.producto.id));
                onGuardarLista(
                  lineas.map((l) => ({ producto_id: l.producto.id, unidades: l.envases })),
                  plan.id,
                );
              }}
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
              {m.feedback && (
                <TarjetaValoracion
                  sujeto={m.feedback}
                  valorado={m.valorado}
                  onValorar={(valor) => onFeedback(m.id, m.feedback!, valor)}
                />
              )}
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
      {chips && !cargando && (
        <div className="mt-4 flex flex-wrap gap-2 pl-14" aria-label="Respuestas rápidas">
          {chips.textos.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => onChip(t, chips)}
              className="rounded-full border border-brand/30 bg-white px-4 py-2 text-[15px] font-semibold text-brand transition hover:bg-brand-wash active:scale-[0.97]"
            >
              {t}
            </button>
          ))}
        </div>
      )}
      <div ref={finRef} />
    </section>
  );
}

// "¿Qué tal salió X?": the dish and two buttons. Once answered, it shows the answer and locks.
function TarjetaValoracion({
  sujeto,
  valorado,
  onValorar,
}: {
  sujeto: SujetoPendiente;
  valorado?: "positivo" | "negativo";
  onValorar: (valor: "positivo" | "negativo") => void;
}) {
  const boton = (valor: "positivo" | "negativo", emoji: string, etiqueta: string) => (
    <button
      type="button"
      aria-label={etiqueta}
      aria-pressed={valorado === valor}
      disabled={valorado !== undefined}
      onClick={() => onValorar(valor)}
      className={`grid h-11 w-11 place-items-center rounded-full text-xl transition ${
        valorado === valor ? "bg-brand text-white" : "bg-[#f0f3f1] hover:bg-brand-wash"
      } ${valorado !== undefined && valorado !== valor ? "opacity-40" : ""} disabled:cursor-default`}
    >
      {emoji}
    </button>
  );
  return (
    <div className="ml-14 flex max-w-[520px] items-center gap-3 rounded-[20px] border border-black/6 bg-white p-3 shadow-[0_8px_30px_rgba(28,52,42,0.07)]">
      <div className="h-14 w-14 shrink-0 overflow-hidden rounded-[14px] bg-[#f4eee1]">
        {sujeto.imagen && (
          <img
            className="h-full w-full object-cover"
            src={sujeto.imagen}
            alt=""
            loading="lazy"
            onError={(event) => (event.currentTarget.style.visibility = "hidden")}
          />
        )}
      </div>
      <p className="min-w-0 flex-1 text-[15px] font-bold">{sujeto.nombre}</p>
      {boton("positivo", "👍", "Me gustó")}
      {boton("negativo", "👎", "No me gustó")}
    </div>
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
