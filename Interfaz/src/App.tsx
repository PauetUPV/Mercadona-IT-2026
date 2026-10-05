import { useState } from "react";
import { Icon, type IconName } from "./components/Icon";
import { MerchePage } from "./screens/Merche/MerchePage";

type Tab = "Inicio" | "Categorías" | "Merche" | "Listas" | "Cuenta";

const navItems: { name: IconName; label: Tab }[] = [
  { name: "home", label: "Inicio" },
  { name: "grid", label: "Categorías" },
  { name: "search", label: "Merche" },
  { name: "list", label: "Listas" },
  { name: "user", label: "Cuenta" },
];

// App shell: tabs, shared "lista" state, toast. Screens live in src/screens/.
export default function App() {
  const [active, setActive] = useState<Tab>("Merche");
  const [added, setAdded] = useState<string[]>([]);
  const [notice, setNotice] = useState("");
  // Bumping this remounts MerchePage, sending it back to its intro state.
  const [merchePage, setMerchePage] = useState(0);

  function showNotice(text: string) {
    setNotice(text);
    window.setTimeout(() => setNotice(""), 2200);
  }

  function toggleProduct(id: string) {
    const yaEstaba = added.includes(id);
    setAdded((items) => (yaEstaba ? items.filter((i) => i !== id) : [...items, id]));
    showNotice(yaEstaba ? "Producto eliminado de tu lista" : "Producto añadido a tu lista");
  }

  function addAll(ids: string[]) {
    setAdded((items) => [...new Set([...items, ...ids])]);
    showNotice("Ingredientes añadidos a tu lista");
  }

  function selectTab(tab: Tab) {
    if (tab === "Merche" && active === "Merche") setMerchePage((n) => n + 1);
    setActive(tab);
  }

  return (
    <div className="min-h-screen bg-[#f7faf8] text-[#15231d]">
      <div className="mx-auto flex min-h-screen max-w-[1120px] flex-col bg-white shadow-[0_0_80px_rgba(27,62,49,0.08)]">
        {/* Kept mounted so the conversation survives switching tabs. */}
        <div className={active === "Merche" ? "flex flex-1 flex-col" : "hidden"}>
          <MerchePage
            key={merchePage}
            added={added}
            onToggle={toggleProduct}
            onAddAll={addAll}
            onNotice={showNotice}
          />
        </div>

        {active !== "Merche" && (
          <main className="flex-1 px-5 pb-28 pt-7 sm:px-9 sm:pt-9 lg:px-12">
            <h1 className="text-[30px] font-extrabold leading-none tracking-[-0.05em] sm:text-[38px]">
              {active}
            </h1>
            <p className="mt-3 text-[#7b8781]">Próximamente.</p>
          </main>
        )}

        <nav className="fixed inset-x-0 bottom-0 z-30 mx-auto h-[76px] max-w-[1120px] border-t border-black/5 bg-white/95 px-2 backdrop-blur sm:h-[82px]">
          <div className="mx-auto flex h-full max-w-[850px] items-center justify-between">
            {navItems.map((item) => {
              const isActive = active === item.label;
              return (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => selectTab(item.label)}
                  className={`relative flex h-[62px] min-w-[60px] flex-col items-center justify-center gap-1 rounded-[20px] px-3 text-[11px] font-semibold transition sm:min-w-[90px] sm:text-xs ${
                    isActive
                      ? "bg-brand-tint text-brand"
                      : "text-[#6f7c76] hover:bg-[#f3f6f4]"
                  }`}
                >
                  {item.label === "Listas" && added.length > 0 && (
                    <span className="absolute right-3 top-1.5 grid h-5 min-w-5 place-items-center rounded-full bg-brand-dark px-1 text-[10px] text-white">
                      {added.length}
                    </span>
                  )}
                  <Icon name={item.name} size={22} strokeWidth={2} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </nav>

        {notice && (
          <div
            role="status"
            className="fixed left-1/2 top-5 z-50 -translate-x-1/2 rounded-full bg-brand-dark px-5 py-3 text-sm font-semibold text-white shadow-xl"
          >
            {notice}
          </div>
        )}
      </div>
    </div>
  );
}
