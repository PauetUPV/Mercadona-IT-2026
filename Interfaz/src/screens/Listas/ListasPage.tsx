import { useState } from "react";
import { Icon } from "../../components/Icon";
import type { ListaGuardada, Producto } from "../../data/types";
import { formatPrecio, formatTamano } from "../../lib/formato";

// The "Listas" tab: lists saved from Merche's plans (with the store picked) and loose products
// added from the search. Everything lives in the browser (see App.tsx).
export function ListasPage({
  listas,
  sueltos,
  onBorrarLista,
  onQuitarSuelto,
}: {
  listas: ListaGuardada[];
  sueltos: Producto[];
  onBorrarLista: (id: string) => void;
  onQuitarSuelto: (producto: Producto) => void;
}) {
  const [abierta, setAbierta] = useState<string | null>(listas[0]?.id ?? null);
  const vacio = listas.length === 0 && sueltos.length === 0;

  return (
    <main className="flex-1 px-5 pb-28 pt-7 sm:px-9 sm:pt-9 lg:px-12">
      <h1 className="text-[30px] font-extrabold leading-none tracking-[-0.05em] sm:text-[38px]">Listas</h1>

      {vacio && (
        <p className="mt-4 max-w-[520px] text-[17px] leading-relaxed text-[#4d5b54]">
          Aún no tienes listas. Pídele a Merche un plan y pulsa «Añadir en una nueva lista», o añade productos desde la búsqueda.
        </p>
      )}

      {listas.length > 0 && (
        <section aria-label="Listas guardadas" className="mt-6 flex flex-col gap-3">
          {listas.map((lista) => {
            const abiertaEsta = abierta === lista.id;
            const envases = lista.lineas.reduce((acc, l) => acc + l.envases, 0);
            return (
              <article
                key={lista.id}
                className="rounded-[24px] border border-black/6 bg-white shadow-[0_8px_30px_rgba(28,52,42,0.07)]"
              >
                <button
                  type="button"
                  aria-expanded={abiertaEsta}
                  onClick={() => setAbierta(abiertaEsta ? null : lista.id)}
                  className="flex w-full items-center gap-3 p-4 text-left sm:p-5"
                >
                  <span className="grid h-12 w-12 shrink-0 place-items-center rounded-[16px] bg-brand-wash text-brand">
                    <Icon name="list" size={22} strokeWidth={2.1} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[17px] font-bold">{lista.nombre}</span>
                    <span className="mt-0.5 block text-sm text-[#708078]">
                      {lista.tienda ? `Mercadona ${lista.tienda}` : "Sin tienda elegida"} · {envases}{" "}
                      {envases === 1 ? "producto" : "productos"}
                    </span>
                  </span>
                  <strong className="text-[17px]">{formatPrecio(lista.total)}</strong>
                  <span
                    aria-hidden
                    className={`text-xl text-[#7b8781] transition-transform duration-200 ${abiertaEsta ? "rotate-90" : ""}`}
                  >
                    ›
                  </span>
                </button>

                {abiertaEsta && (
                  <div className="border-t border-black/6 px-4 pb-4 sm:px-5">
                    <ul className="divide-y divide-black/6">
                      {lista.lineas.map((l) => (
                        <li key={l.producto.id} className="flex items-center gap-3 py-2.5">
                          <div className="h-11 w-11 shrink-0 overflow-hidden rounded-[12px] bg-[#f4eee1]">
                            <img
                              className="h-full w-full object-cover"
                              src={l.producto.thumbnail}
                              alt=""
                              loading="lazy"
                              onError={(event) => (event.currentTarget.style.visibility = "hidden")}
                            />
                          </div>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-[15px] font-semibold">{l.producto.nombre}</span>
                            <span className="block text-[13px] text-[#7b8781]">
                              {l.envases} × {formatPrecio(l.producto.precio)}
                            </span>
                          </span>
                          <span className="text-[15px] text-[#4d5b54]">{formatPrecio(l.subtotal)}</span>
                        </li>
                      ))}
                    </ul>
                    <div className="mt-2 flex items-center justify-between border-t border-black/6 pt-3">
                      <button
                        type="button"
                        onClick={() => onBorrarLista(lista.id)}
                        className="text-sm font-semibold text-[#7b8781] transition hover:text-[#15231d]"
                      >
                        Borrar lista
                      </button>
                      <p className="text-[15px]">
                        <span className="font-semibold text-[#4d5b54]">Total </span>
                        <strong className="text-lg">{formatPrecio(lista.total)}</strong>
                      </p>
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </section>
      )}

      {sueltos.length > 0 && (
        <section aria-label="Productos añadidos" className="mt-8">
          <h2 className="text-lg font-bold">Productos añadidos</h2>
          <ul className="mt-2 divide-y divide-black/6">
            {sueltos.map((p) => (
              <li key={p.id} className="flex items-center gap-3 py-2.5">
                <div className="h-11 w-11 shrink-0 overflow-hidden rounded-[12px] bg-[#f4eee1]">
                  <img
                    className="h-full w-full object-cover"
                    src={p.thumbnail}
                    alt=""
                    loading="lazy"
                    onError={(event) => (event.currentTarget.style.visibility = "hidden")}
                  />
                </div>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[15px] font-semibold">{p.nombre}</span>
                  <span className="block text-[13px] text-[#7b8781]">{formatTamano(p.tamano, p.formato_tamano)}</span>
                </span>
                <span className="text-[15px] text-[#4d5b54]">{formatPrecio(p.precio)}</span>
                <button
                  type="button"
                  aria-label={`Quitar ${p.nombre}`}
                  onClick={() => onQuitarSuelto(p)}
                  className="grid h-9 w-9 place-items-center rounded-full bg-[#f0f3f1] text-[#4d5b54] transition hover:bg-[#e6ebe8]"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
