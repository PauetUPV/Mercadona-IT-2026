import type { Plan } from "../../data/types";
import { formatPrecio } from "../../lib/formato";

type Dia = Plan["dias"][number];

// Vista independiente de un plato: sus ingredientes con checkbox.
export function PlatoDetalle({
    dia,
    seleccion,
    subtotal,
    onToggle,
    onVolver,
}: {
    dia: Dia;
    seleccion: Set<string>;
    subtotal: number;
    onToggle: (id: string) => void;
    onVolver: () => void;
}) {
    const { receta } = dia;

    return (
        <section aria-label={`Ingredientes de ${receta.nombre}`} className="pt-5">
            <button
                type="button"
                onClick={onVolver}
                className="mb-4 text-sm font-semibold text-brand transition hover:text-brand-hover"
            >
                ‹ Volver a tu plan
            </button>

            <div className="rounded-[24px] border border-black/6 bg-white p-4 shadow-[0_8px_30px_rgba(28,52,42,0.07)] sm:p-5">
                <div className="flex items-center gap-3">
                    <div className="h-14 w-14 shrink-0 overflow-hidden rounded-[14px] bg-[#f4eee1]">
                        <img
                            className="h-full w-full object-cover"
                            src={receta.imagen}
                            alt=""
                            loading="lazy"
                            onError={(event) => (event.currentTarget.style.visibility = "hidden")}
                        />
                    </div>
                    <div className="min-w-0 flex-1">
                        <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-[#7b8781]">
                            {dia.dia}
                        </p>
                        <h3 className="text-[17px] font-bold">{receta.nombre}</h3>
                    </div>
                </div>

                <h4 className="mt-6 text-lg font-bold">Ingredientes</h4>

                <ul className="mt-1 divide-y divide-black/6">
                    {receta.ingredientes.map((ing) => (
                        <li key={ing.id}>
                            <label className="flex cursor-pointer items-center gap-3 py-3">
                                <input
                                    type="checkbox"
                                    checked={seleccion.has(ing.id)}
                                    onChange={() => onToggle(ing.id)}
                                    className="h-5 w-5 shrink-0 accent-brand"
                                />
                                <span
                                    className={`min-w-0 flex-1 truncate text-[15px] font-semibold ${seleccion.has(ing.id) ? "" : "text-[#7b8781] line-through"
                                        }`}
                                >
                                    {ing.nombre}
                                </span>
                                <span className="text-[15px] text-[#4d5b54]">{formatPrecio(ing.precio)}</span>
                            </label>
                        </li>
                    ))}
                </ul>

                <p className="mt-2 flex items-center justify-between border-t border-black/6 pt-3 text-[15px]">
                    <span className="font-semibold text-[#4d5b54]">
                        Subtotal · {seleccion.size} de {receta.ingredientes.length}
                    </span>
                    <strong className="text-lg">{formatPrecio(subtotal)}</strong>
                </p>
            </div>
        </section>
    );
}