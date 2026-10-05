import { Icon } from "../../components/Icon";

type Sugerencia = { tipo: "buscar" | "merche"; texto: string };

// Read column by column (2 rows): [1 top, 2 bottom], [3 top, 4 bottom]...
// Order is mixed on purpose so both paths show up in every row and column.
// Keep every "merche" prompt long or question-like, and every "buscar" one short,
// so they route as labelled.
const SUGERENCIAS: Sugerencia[] = [
  { tipo: "merche", texto: "Hola Merche, ¿qué puedo cenar esta noche con pasta?" },
  { tipo: "buscar", texto: "tomate" },
  { tipo: "buscar", texto: "huevos camperos" },
  { tipo: "merche", texto: "Somos 4 en casa y tenemos 90 € para la semana, ¿me ayudas con las comidas?" },
  { tipo: "merche", texto: "El martes no me apetece cocinar, ¿qué me recomiendas?" },
  { tipo: "merche", texto: "Quiero preparar algo especial para el domingo, ¿me das ideas?" },
  { tipo: "buscar", texto: "arroz" },
  { tipo: "buscar", texto: "pechuga de pollo" },
  { tipo: "buscar", texto: "macarrones" },
  { tipo: "merche", texto: "Quiero comer más ligero esta semana, ¿me propones un menú?" },
  { tipo: "merche", texto: "Tengo pollo y arroz en la nevera, ¿qué receta me sugieres?" },
  { tipo: "buscar", texto: "queso rallado" },
];

const ETIQUETA = { buscar: "Buscar un producto", merche: "Preguntar a Merche" } as const;

// State A: nothing sent yet. Explains the single bar and teaches both paths by example.
export function IntroBlock({ onEjemplo }: { onEjemplo: (texto: string) => void }) {
  return (
    <section aria-label="Cómo usar Merche" className="pt-6">
      <h2 className="text-[26px] font-extrabold leading-tight tracking-[-0.03em] sm:text-[30px]">
        ¿Qué necesitas hoy?
      </h2>
      <p className="mt-3 max-w-[560px] text-[17px] leading-relaxed text-[#4d5b54] sm:text-lg">
        Busca un producto como siempre, o pídele a Merche un menú, una receta o
        un plan semanal.
      </p>

      <p className="mt-8 text-xs font-bold uppercase tracking-[0.12em] text-[#7b8781]">
        Prueba con
      </p>
      {/* Bleeds to the screen edges; px keeps the first/last tile off them. scroll-px stops snapping from eating that padding. */}
      <div className="-mx-5 mt-3 snap-x overflow-x-auto px-5 pb-2 scroll-px-5 [scrollbar-width:none] sm:-mx-9 sm:px-9 sm:scroll-px-9 lg:-mx-12 lg:px-12 lg:scroll-px-12 [&::-webkit-scrollbar]:hidden">
        <div className="grid w-max grid-flow-col grid-rows-2 auto-cols-[172px] gap-3 pr-5 sm:auto-cols-[200px] sm:pr-9 lg:pr-12">
          {SUGERENCIAS.map((s) => (
            <button
              key={s.texto}
              type="button"
              onClick={() => onEjemplo(s.texto)}
              className={`snap-start rounded-[22px] p-4 text-left transition active:scale-[0.97] ${
                s.tipo === "merche"
                  ? "bg-brand-tile hover:bg-brand-tile-hover"
                  : "bg-[#f0f3f1] hover:bg-[#e6ebe8]"
              }`}
            >
              <span
                className={`flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.08em] ${
                  s.tipo === "merche" ? "text-brand" : "text-[#7b8781]"
                }`}
              >
                <Icon name={s.tipo === "merche" ? "chef" : "search"} size={14} strokeWidth={2.4} />
                {ETIQUETA[s.tipo]}
              </span>
              <span className="mt-2 block text-[15px] font-semibold leading-snug text-[#15231d]">
                {s.tipo === "merche" ? s.texto : `«${s.texto}»`}
              </span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
