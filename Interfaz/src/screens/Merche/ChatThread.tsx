import { useEffect, useRef, type ReactNode } from "react";
import { Icon } from "../../components/Icon";
import { ProductRow } from "../../components/ProductRow";
import type { MensajeChat, Plan, Producto } from "../../data/types";
import { formatPrecio } from "../../lib/formato";

const ingredientesUnicos = (plan: Plan): Producto[] => {
  const porId = new Map<string, Producto>();
  plan.dias.forEach((d) => d.receta.ingredientes.forEach((i) => porId.set(i.id, i)));
  return [...porId.values()];
};

// State C: conversation with Merche, plus the plan she proposes.
export function ChatThread({
  mensajes,
  plan,
  cargando,
  added,
  onToggle,
  onAddAll,
  onNotice,
}: {
  mensajes: MensajeChat[];
  plan?: Plan;
  cargando: boolean;
  added: string[];
  onToggle: (id: string) => void;
  onAddAll: (ids: string[]) => void;
  onNotice: (texto: string) => void;
}) {
  const finRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensajes.length, cargando, plan]);

  const ingredientes = plan ? ingredientesUnicos(plan) : [];

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
            <h3 className="text-[17px] font-bold">Tu plan · {plan.comensales} personas</h3>
            <ul className="mt-2 divide-y divide-black/6">
              {plan.dias.map((d) => (
                <li key={d.dia} className="flex items-center gap-3 py-3">
                  <div className="h-14 w-14 shrink-0 overflow-hidden rounded-[14px] bg-[#f4eee1]">
                    <img
                      className="h-full w-full object-cover"
                      src={d.receta.imagen}
                      alt=""
                      loading="lazy"
                      onError={(event) => (event.currentTarget.style.visibility = "hidden")}
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-[#7b8781]">
                      {d.dia}
                    </p>
                    <p className="truncate text-[15px] font-bold">{d.receta.nombre}</p>
                  </div>
                  <strong className="text-[15px]">{formatPrecio(d.receta.precio)}</strong>
                </li>
              ))}
            </ul>
            <p className="mt-2 flex items-center justify-between border-t border-black/6 pt-3 text-[15px]">
              <span className="font-semibold text-[#4d5b54]">
                Total{plan.presupuesto ? ` (presupuesto ${formatPrecio(plan.presupuesto)})` : ""}
              </span>
              <strong className="text-lg">{formatPrecio(plan.total)}</strong>
            </p>
          </div>

          {ingredientes.length > 0 && (
            <>
              <h3 className="mt-6 text-lg font-bold">Ingredientes</h3>
              <div className="mt-1 divide-y divide-black/6">
                {ingredientes.map((producto) => (
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
              onClick={() => onAddAll(ingredientes.map((i) => i.id))}
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
