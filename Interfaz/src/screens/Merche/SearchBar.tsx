import type { FormEvent } from "react";
import { Icon } from "../../components/Icon";
import type { Intencion } from "../../data/types";

// The single input. The hint above it shows where the text will go before sending.
export function SearchBar({
  value,
  onChange,
  onSubmit,
  intencion,
}: {
  value: string;
  onChange: (texto: string) => void;
  onSubmit: () => void;
  intencion: Intencion;
}) {
  const esMerche = intencion === "merche";

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <div className="fixed inset-x-0 bottom-[90px] z-20 mx-auto max-w-[1120px] px-4 sm:bottom-[96px] sm:px-9 lg:px-12">
      {value.trim() && (
        <span
          role="status"
          className={`mb-2 ml-3 inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold shadow-sm ${
            esMerche ? "bg-brand text-white" : "bg-brand-dark text-white"
          }`}
        >
          <Icon name={esMerche ? "chef" : "search"} size={14} strokeWidth={2.4} />
          {esMerche ? "Preguntar a Merche" : "Buscar producto"}
        </span>
      )}
      <form
        onSubmit={handleSubmit}
        className="flex h-[62px] items-center gap-3 rounded-[23px] border border-black/5 bg-[#f2f5f3]/95 px-4 shadow-[0_10px_35px_rgba(31,74,50,0.13)] backdrop-blur"
      >
        <span className="text-[#718078]">
          <Icon name="search" size={24} />
        </span>
        <input
          className="min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-[#89938e]"
          placeholder="Busca un producto o pídele a Merche un menú, una receta…"
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
        <button
          aria-label={esMerche ? "Enviar a Merche" : "Buscar"}
          className={`grid h-11 w-11 shrink-0 place-items-center rounded-full text-white shadow-[0_7px_18px_rgba(66,148,100,0.25)] transition active:scale-95 ${
            esMerche ? "bg-brand hover:bg-brand-hover" : "bg-brand-dark hover:bg-brand-dark-hover"
          }`}
          type="submit"
        >
          <Icon name={esMerche ? "send" : "search"} size={21} strokeWidth={2.1} />
        </button>
      </form>
    </div>
  );
}
