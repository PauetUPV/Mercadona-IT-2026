import type { Producto } from "../data/types";
import { formatPrecio } from "../lib/formato";
import { Icon } from "./Icon";

// Mercadona-style product row. Shared by search results and Merche's plan.
export function ProductRow({
  producto,
  added,
  onToggle,
}: {
  producto: Producto;
  added: boolean;
  onToggle: () => void;
}) {
  return (
    <article className="flex items-center gap-4 py-3">
      <div className="h-[72px] w-[72px] shrink-0 overflow-hidden rounded-[16px] bg-[#f4eee1]">
        <img
          className="h-full w-full object-cover"
          src={producto.imagen}
          alt=""
          loading="lazy"
          onError={(event) => (event.currentTarget.style.visibility = "hidden")}
        />
      </div>
      <div className="min-w-0 flex-1">
        <h3 className="truncate text-[16px] font-bold leading-tight text-[#15231d]">
          {producto.nombre}
        </h3>
        <p className="mt-0.5 truncate text-sm text-[#708078]">{producto.detalle}</p>
        <strong className="mt-1 block text-[17px] tracking-tight text-[#13231c]">
          {formatPrecio(producto.precio)}
        </strong>
      </div>
      <button
        type="button"
        aria-label={added ? `Quitar ${producto.nombre} de tu lista` : `Añadir ${producto.nombre} a tu lista`}
        aria-pressed={added}
        onClick={onToggle}
        className={`grid h-11 w-11 shrink-0 place-items-center rounded-full text-white transition active:scale-95 ${
          added ? "bg-brand-dark" : "bg-brand hover:bg-brand-hover"
        }`}
      >
        <Icon name={added ? "check" : "plus"} size={21} strokeWidth={2.2} />
      </button>
    </article>
  );
}
