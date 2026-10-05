import { useEffect, useRef, useState } from "react";
import { Icon } from "../../components/Icon";
import { bienvenida, buscarProductos, enviarMensaje, guardarLista, nuevaSesion, valorar } from "../../data/service";
import type { Intencion, LineaLista, MensajeChat, Plan, Producto, RespuestaChat, SujetoPendiente } from "../../data/types";
import { decidirIntencion } from "../../lib/intencion";
import { ChatThread, type Chips } from "./ChatThread";
import { IntroBlock } from "./IntroBlock";
import { SearchBar } from "./SearchBar";
import { SearchResults } from "./SearchResults";

// One screen, three bodies. The bar below never changes; only what's above it does.
type Vista =
  | { tipo: "vacio" }
  | { tipo: "busqueda"; consulta: string; resultados: Producto[] | null }
  | {
      tipo: "conversacion";
      mensajes: MensajeChat[];
      plan?: Plan;
      planEn?: string;
      conclusion?: string;
      chips?: Chips;
      cargando: boolean;
    };

// What a turn ends with: the chat reply, or a rating reply that may bring its own reason chips.
type Respuesta = RespuestaChat & { chips?: Chips };

const SIN_CONEXION = "Ahora mismo no puedo conectar. Inténtalo de nuevo en un momento.";

let nMensajes = 0;
const deMerche = (texto: string, feedback?: SujetoPendiente): MensajeChat => ({
  id: `m${++nMensajes}`,
  autor: "merche",
  texto,
  feedback,
});
const delUsuario = (texto: string): MensajeChat => ({ id: `u${++nMensajes}`, autor: "usuario", texto });

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
  // The plan as the user edited it (unticked dishes/ingredients), if they did since the last response.
  const [planEditado, setPlanEditado] = useState<Plan | undefined>();

  // Inside a conversation, follow-ups ("cambia el martes") always go to Merche.
  const intencion: Intencion =
    vista.tipo === "conversacion" ? "merche" : decidirIntencion(texto);

  // Merche may open the conversation herself: "¿Qué tal salió la lasaña?" (after a saved list).
  // A plain greeting is not shown: the intro block already greets.
  const abierto = useRef(false);
  useEffect(() => {
    if (abierto.current) return;
    abierto.current = true;
    bienvenida()
      .then((r) => {
        if (!r.feedback) return;
        setVista((v) =>
          v.tipo === "vacio"
            ? { tipo: "conversacion", mensajes: [deMerche(r.mensaje, r.feedback)], chips: chipsDe(r), cargando: false }
            : v,
        );
      })
      .catch(() => undefined); // no backend: the intro block is enough
  }, []);

  const chipsDe = (r: { sugerencias?: string[] | null }, motivoDe?: SujetoPendiente): Chips | undefined =>
    r.sugerencias && r.sugerencias.length > 0 ? { textos: r.sugerencias, motivoDe } : undefined;

  // Shows the user's bubble (if any) and "pensando…" while `peticion` runs, then Merche's answer.
  async function turno(usuario: string | null, peticion: () => Promise<Respuesta>) {
    const burbuja = usuario ? [delUsuario(usuario)] : [];
    setVista((v) =>
      v.tipo === "conversacion"
        ? { ...v, mensajes: [...v.mensajes, ...burbuja], conclusion: undefined, chips: undefined, cargando: true }
        : { tipo: "conversacion", mensajes: burbuja, cargando: true },
    );
    let respuesta: Respuesta;
    try {
      respuesta = await peticion();
    } catch {
      respuesta = { mensaje: SIN_CONEXION };
    }
    const merche = deMerche(respuesta.mensaje, respuesta.feedback);
    if (respuesta.plan) setPlanEditado(undefined); // a new plan starts clean
    setVista((v) =>
      v.tipo === "conversacion"
        ? {
            ...v,
            mensajes: [...v.mensajes, merche],
            plan: respuesta.plan ?? v.plan, // no plan in the response = nothing changed
            planEn: respuesta.plan ? merche.id : v.planEn,
            conclusion: respuesta.conclusion,
            chips: respuesta.chips ?? chipsDe(respuesta),
            cargando: false,
          }
        : v,
    );
  }

  async function buscar(consulta: string) {
    setVista({ tipo: "busqueda", consulta, resultados: null });
    const resultados = await buscarProductos(consulta).catch(() => [] as Producto[]);
    setVista((v) =>
      v.tipo === "busqueda" && v.consulta === consulta ? { ...v, resultados } : v,
    );
  }

  function preguntarAMerche(consulta: string) {
    const editado = planEditado;
    setPlanEditado(undefined); // sent once: the backend now keeps it as the current plan
    return turno(consulta, () => enviarMensaje(consulta, editado));
  }

  // Thumbs up/down on a rating card. A thumbs down first asks why (reason chips).
  function responderFeedback(mensajeId: string, sujeto: SujetoPendiente, valor: "positivo" | "negativo") {
    setVista((v) =>
      v.tipo === "conversacion"
        ? { ...v, mensajes: v.mensajes.map((m) => (m.id === mensajeId ? { ...m, valorado: valor } : m)) }
        : v,
    );
    return turno(null, async () => {
      const r = await valorar(sujeto, valor);
      return { mensaje: r.mensaje ?? "¡Gracias!", feedback: r.feedback ?? undefined, chips: chipsDe(r, sujeto) };
    });
  }

  // A chip is either a message for Merche or, after a thumbs down, the reason why.
  function pulsarChip(textoChip: string, chips: Chips) {
    if (!chips.motivoDe) return preguntarAMerche(textoChip);
    const sujeto = chips.motivoDe;
    return turno(textoChip, async () => {
      const r = await valorar(sujeto, "negativo", textoChip);
      return { mensaje: r.mensaje ?? "¡Gracias!", feedback: r.feedback ?? undefined, chips: chipsDe(r) };
    });
  }

  // "Añadir en una nueva lista": the backend needs to know what was bought to ask later how it went.
  async function guardar(lineas: LineaLista[], planId?: string) {
    try {
      const r = await guardarLista(lineas, planId);
      if (r.mensaje) {
        const mensaje = deMerche(r.mensaje);
        setVista((v) => (v.tipo === "conversacion" ? { ...v, mensajes: [...v.mensajes, mensaje], conclusion: undefined } : v));
      }
    } catch {
      onNotice("No se ha podido guardar la lista en Merche");
    }
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
    setPlanEditado(undefined);
    nuevaSesion();
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
            planEn={vista.planEn}
            conclusion={vista.conclusion}
            chips={vista.chips}
            cargando={vista.cargando}
            onAddAll={onAddAll}
            onGuardarLista={(lineas, planId) => void guardar(lineas, planId)}
            onPlanEditado={setPlanEditado}
            onChip={(t, chips) => void pulsarChip(t, chips)}
            onFeedback={(id, sujeto, valor) => void responderFeedback(id, sujeto, valor)}
          />
        )}
      </main>

      <SearchBar
        value={texto}
        onChange={setTexto}
        onSubmit={() => enviar(texto)}
        intencion={intencion}
        soloMerche={vista.tipo === "conversacion"}
      />
    </>
  );
}
