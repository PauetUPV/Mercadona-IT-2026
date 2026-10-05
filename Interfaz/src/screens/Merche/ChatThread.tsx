import { useEffect, useRef, useState, type ReactNode } from "react";
import { Icon } from "../../components/Icon";
import type { MensajeChat, Plan } from "../../data/types";
import { formatPrecio } from "../../lib/formato";
import { PlatoDetalle } from "./PlatoDetalle";

// Evita arrastres de coma flotante (0.1 + 0.2) al sumar precios.
const redondear = (n: number) => Math.round(n * 100) / 100;

// State C: conversation with Merche, plus the plan she proposes.
// Each dish in the plan opens its own view with selectable ingredients.
export function ChatThread({
    mensajes,
    plan,
    cargando,
    onNotice,
}: {
    mensajes: MensajeChat[];
    plan?: Plan;
    cargando: boolean;
    // Se mantienen en la firma para no tocar MerchePage; ya no se usan aquí.
    added?: string[];
    onToggle?: (id: string) => void;
    onAddAll?: (ids: string[]) => void;
    onNotice: (texto: string) => void;
}) {
    const finRef = useRef<HTMLDivElement>(null);
    const [platoAbierto, setPlatoAbierto] = useState<number | null>(null);
    const [selecciones, setSelecciones] = useState<Record<number, Set<string>>>({});

    useEffect(() => {
        finRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }, [mensajes.length, cargando, plan]);

    // Un plan nuevo empieza limpio.
    useEffect(() => {
        setPlatoAbierto(null);
        setSelecciones({});
    }, [plan]);

    // Por defecto todos los ingredientes aparecen marcados.
    const seleccionDe = (i: number): Set<string> =>
        selecciones[i] ?? new Set(plan?.dias[i].receta.ingredientes.map((x) => x.id) ?? []);

    // Suma solo los ingredientes marcados del plato i.
    const subtotalDe = (i: number): number => {
        const marcados = seleccionDe(i);
        const suma = (plan?.dias[i].receta.ingredientes ?? [])
            .filter((ing) => marcados.has(ing.id))
            .reduce((acc, ing) => acc + ing.precio, 0);
        return redondear(suma);
    };

    function toggleIngrediente(i: number, id: string) {
        setSelecciones((prev) => {
            const next = new Set(prev[i] ?? seleccionDe(i));
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return { ...prev, [i]: next };
        });
    }

    const totalSeleccionado = plan
        ? redondear(plan.dias.reduce((acc, _d, i) => acc + subtotalDe(i), 0))
        : 0;

    if (plan && platoAbierto !== null && plan.dias[platoAbierto]) {
        return (
            <PlatoDetalle
                dia={plan.dias[platoAbierto]}
                seleccion={seleccionDe(platoAbierto)}
                subtotal={subtotalDe(platoAbierto)}
                onToggle={(id) => toggleIngrediente(platoAbierto, id)}
                onVolver={() => setPlatoAbierto(null)}
            />
        );
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

                {plan && (
                    <div className="mt-5">
                        <div className="rounded-[24px] border border-black/6 bg-white p-4 shadow-[0_8px_30px_rgba(28,52,42,0.07)] sm:p-5">
                            <h3 className="text-[17px] font-bold">Tu plan · {plan.comensales} personas</h3>

                            <ul className="mt-2 divide-y divide-black/6">
                                {plan.dias.map((d, i) => (
                                    <li key={d.dia}>
                                        <button
                                            type="button"
                                            onClick={() => setPlatoAbierto(i)}
                                            className="flex w-full items-center gap-3 py-3 text-left transition hover:bg-brand-wash"
                                        >
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
                                            <strong className="text-[15px]">{formatPrecio(subtotalDe(i))}</strong>
                                            <span aria-hidden className="text-xl text-[#7b8781]">
                                                ›
                                            </span>
                                        </button>
                                    </li>
                                ))}
                            </ul>

                            <p className="mt-2 flex items-center justify-between border-t border-black/6 pt-3 text-[15px]">
                                <span className="font-semibold text-[#4d5b54]">
                                    Total
                                    {plan.presupuesto ? ` (presupuesto ${formatPrecio(plan.presupuesto)})` : ""}
                                </span>
                                <strong
                                    className={`text-lg ${plan.presupuesto && totalSeleccionado > plan.presupuesto ? "text-red-600" : ""
                                        }`}
                                >
                                    {formatPrecio(totalSeleccionado)}
                                </strong>
                            </p>
                        </div>

                        <div className="mt-4 flex flex-wrap gap-2.5">
                            {/* Solo estético: sin onClick a propósito. */}
                            <button
                                type="button"
                                className="flex h-12 flex-1 items-center justify-center gap-2 rounded-full bg-brand px-5 text-sm font-bold text-white transition hover:bg-brand-hover sm:flex-none"
                            >
                                <Icon name="list" size={20} />
                                Añadir a la lista de la compra
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
            </div>
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