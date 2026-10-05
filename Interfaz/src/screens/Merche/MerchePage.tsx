import { useState } from "react";
import { Icon } from "../../components/Icon";
import { buscarProductos, enviarMensaje } from "../../data/service";
import type { Intencion, MensajeChat, Plan, Producto } from "../../data/types";
import { decidirIntencion } from "../../lib/intencion";
import { ChatThread } from "./ChatThread";
import { IntroBlock } from "./IntroBlock";
import { SearchBar } from "./SearchBar";
import { SearchResults } from "./SearchResults";

// One screen, three bodies. The bar below never changes; only what's above it does.
type Vista =
  | { tipo: "vacio" }
  | { tipo: "busqueda"; consulta: string; resultados: Producto[] | null }
  | { tipo: "conversacion"; mensajes: MensajeChat[]; plan?: Plan; cargando: boolean };

let nMensajes = 0;

export function MerchePage({
  added,
  onToggle,
  onAddAll,
  onNotice,
}: {
  added: string[];
  onToggle: (id: string) => void;
  onAddAll: (ids: string[]) => void;
  onNotice: (texto: string) => void;
}) {
  const [vista, setVista] = useState<Vista>({ tipo: "vacio" });
  const [texto, setTexto] = useState("");

  // Inside a conversation, follow-ups ("cambia el martes") always go to Merche.
  const intencion: Intencion =
    vista.tipo === "conversacion" ? "merche" : decidirIntencion(texto);

  async function buscar(consulta: string) {
    setVista({ tipo: "busqueda", consulta, resultados: null });
    const resultados = await buscarProductos(consulta);
    setVista((v) =>
      v.tipo === "busqueda" && v.consulta === consulta ? { ...v, resultados } : v,
    );
  }

  async function preguntarAMerche(consulta: string) {
    const usuario: MensajeChat = { id: `u${++nMensajes}`, autor: "usuario", texto: consulta };
    setVista((v) =>
      v.tipo === "conversacion"
        ? { ...v, mensajes: [...v.mensajes, usuario], cargando: true }
        : { tipo: "conversacion", mensajes: [usuario], cargando: true },
    );
    const respuesta = await enviarMensaje(consulta);
    setVista((v) =>
      v.tipo === "conversacion"
        ? {
            ...v,
            mensajes: [...v.mensajes, respuesta.mensaje],
            plan: respuesta.plan ?? v.plan,
            cargando: false,
          }
        : v,
    );
  }

  function enviar(consulta: string, forzar?: Intencion) {
    const limpio = consulta.trim();
    if (!limpio) return;
    setTexto("");
    const destino =
      forzar ?? (vista.tipo === "conversacion" ? "merche" : decidirIntencion(limpio));
    if (destino === "merche") void preguntarAMerche(limpio);
    else void buscar(limpio);
  }

  function reiniciar() {
    setVista({ tipo: "vacio" });
    setTexto("");
  }

  return (
    <>
      <header className="flex items-center gap-1 px-5 pb-2 pt-7 sm:px-9 sm:pt-9 lg:px-12">
        {vista.tipo !== "vacio" && (
          <button
            type="button"
            onClick={reiniciar}
            aria-label="Volver"
            className="-ml-3 grid h-10 w-10 shrink-0 place-items-center rounded-full text-brand transition hover:bg-brand-wash active:scale-95"
          >
            <Icon name="back" size={28} strokeWidth={2.4} />
          </button>
        )}
        <h1 className="text-[30px] font-extrabold leading-none tracking-[-0.05em] sm:text-[38px]">
          Merche
        </h1>
      </header>

      <main className="flex-1 px-5 pb-48 sm:px-9 lg:px-12">
        {vista.tipo === "vacio" && <IntroBlock onEjemplo={(t) => enviar(t)} />}
        {vista.tipo === "busqueda" && (
          <SearchResults
            consulta={vista.consulta}
            resultados={vista.resultados}
            added={added}
            onToggle={onToggle}
            onPreguntarMerche={() => enviar(vista.consulta, "merche")}
          />
        )}
        {vista.tipo === "conversacion" && (
          <ChatThread
            mensajes={vista.mensajes}
            plan={vista.plan}
            cargando={vista.cargando}
            added={added}
            onToggle={onToggle}
            onAddAll={onAddAll}
            onNotice={onNotice}
          />
        )}
      </main>

      <SearchBar
        value={texto}
        onChange={setTexto}
        onSubmit={() => enviar(texto)}
        intencion={intencion}
      />
    </>
  );
}
