import { Icon } from "../../components/Icon";
import { ProductRow } from "../../components/ProductRow";
import type { Producto } from "../../data/types";

// State B: classic product search. `resultados === null` means still loading.
export function SearchResults({
  consulta,
  resultados,
  added,
  onToggle,
  onPreguntarMerche,
}: {
  consulta: string;
  resultados: Producto[] | null;
  added: string[];
  onToggle: (id: string) => void;
  onPreguntarMerche: () => void;
}) {
  return (
    <section aria-label="Resultados de búsqueda" className="pt-5">
      <h2 className="text-lg font-bold text-[#15231d]">
        {resultados === null
          ? `Buscando «${consulta}»…`
          : resultados.length === 0
            ? `No hemos encontrado «${consulta}»`
            : `${resultados.length} resultados para «${consulta}»`}
      </h2>

      {resultados && resultados.length > 0 && (
        <div className="mt-2 divide-y divide-black/6">
          {resultados.map((producto) => (
            <ProductRow
              key={producto.id}
              producto={producto}
              added={added.includes(producto.id)}
              onToggle={() => onToggle(producto.id)}
            />
          ))}
        </div>
      )}

      {resultados && (
        <button
          type="button"
          onClick={onPreguntarMerche}
          className="mt-5 flex w-full items-center gap-3 rounded-[20px] bg-brand-wash px-4 py-3.5 text-left transition hover:bg-brand-tint active:scale-[0.99]"
        >
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-[14px] bg-brand text-white">
            <Icon name="chef" size={21} strokeWidth={2.1} />
          </span>
          <span>
            <span className="block text-[15px] font-bold text-[#15231d]">
              ¿No es lo que buscabas?
            </span>
            <span className="block text-sm text-[#4d5b54]">
              Pregúntale a Merche por «{consulta}»
            </span>
          </span>
        </button>
      )}
    </section>
  );
}
