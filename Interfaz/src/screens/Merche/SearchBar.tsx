import type { FormEvent } from "react";
import { Icon } from "../../components/Icon";
import type { Intencion } from "../../data/types";

// The single input. The hint above it shows where the text will go before sending.
export function SearchBar({
  value,
  onChange,
  onSubmit,
  intencion,
  soloMerche = false,
  voz,
}: {
  value: string;
  onChange: (texto: string) => void;
  onSubmit: () => void;
  intencion: Intencion;
  // Inside a conversation there is no product search: the bar only talks to Merche.
  soloMerche?: boolean;
  // Voice: with an empty bar, the button is a microphone (tap to talk, tap again to send).
  voz?: { estado: "parado" | "grabando" | "transcribiendo"; onPulsar: () => void };
}) {
  const esMerche = intencion === "merche";

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  const hayTexto = value.trim() !== "";
  const conVoz = voz && (!hayTexto || voz.estado !== "parado");

  return (
    <div className="fixed inset-x-0 bottom-[90px] z-20 mx-auto max-w-[1120px] px-4 sm:bottom-[96px] sm:px-9 lg:px-12">
      {/* One outlined box: the outline takes the color of the destination, and a
          thicker top edge carries the label once the user starts typing. */}
      <div
        className={`overflow-hidden rounded-full border-2 bg-[#f2f5f3]/95 shadow-[0_10px_35px_rgba(31,74,50,0.13)] backdrop-blur transition-colors ${
          !hayTexto && !soloMerche ? "border-black/5" : esMerche ? "border-brand" : "border-brand-dark"
        }`}
      >
        {!soloMerche && (
        <div
          aria-hidden={!hayTexto}
          className={`grid transition-[grid-template-rows] duration-200 ${
            hayTexto ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
          }`}
        >
          <div className="overflow-hidden">
            <p
              role="status"
              className={`flex items-center justify-center gap-1.5 px-6 py-1.5 text-xs font-bold text-white transition-colors ${esMerche ? "bg-brand" : "bg-brand-dark"}`}
            >
              <Icon name={esMerche ? "chef" : "search"} size={14} strokeWidth={2.4} />
              {esMerche ? "Preguntar a Merche" : "Buscar producto"}
            </p>
          </div>
        </div>
        )}
        <form onSubmit={handleSubmit} className="flex h-[58px] items-center gap-3 pl-5 pr-[7px]">
          <span className="text-[#718078]">
            <Icon name={soloMerche ? "chef" : "search"} size={24} />
          </span>
          <input
            className="min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-[#89938e]"
            disabled={voz && voz.estado !== "parado"}
            placeholder={
              voz?.estado === "grabando"
                ? "Te escucho… pulsa ■ para enviar"
                : voz?.estado === "transcribiendo"
                  ? "Escuchando lo que has dicho…"
                  : soloMerche
                    ? "Pídele a Merche un cambio: «cambia el martes», «más barato»…"
                    : "Busca un producto o pídele a Merche un menú, una receta…"
            }
            value={value}
            onChange={(event) => onChange(event.target.value)}
          />
          {conVoz ? (
            <button
              type="button"
              onClick={voz.onPulsar}
              disabled={voz.estado === "transcribiendo"}
              aria-label={voz.estado === "grabando" ? "Parar y enviar el audio" : "Hablar con Merche"}
              aria-pressed={voz.estado === "grabando"}
              className={`grid h-11 w-11 shrink-0 place-items-center rounded-full text-white shadow-[0_7px_18px_rgba(66,148,100,0.25)] transition active:scale-95 disabled:opacity-60 ${
                voz.estado === "grabando" ? "animate-pulse bg-[#c2410c]" : "bg-brand hover:bg-brand-hover"
              }`}
            >
              <Icon name={voz.estado === "grabando" ? "stop" : "mic"} size={21} strokeWidth={2.1} />
            </button>
          ) : (
          <button
            aria-label={esMerche ? "Enviar a Merche" : "Buscar"}
            className={`grid h-11 w-11 shrink-0 place-items-center rounded-full text-white shadow-[0_7px_18px_rgba(66,148,100,0.25)] transition active:scale-95 ${
              esMerche ? "bg-brand hover:bg-brand-hover" : "bg-brand-dark hover:bg-brand-dark-hover"
            }`}
            type="submit"
          >
            <Icon name={esMerche ? "send" : "search"} size={21} strokeWidth={2.1} />
          </button>
          )}
        </form>
      </div>
    </div>
  );
}
