import { FormEvent, ReactNode, useState } from "react";

type IconName =
  | "home"
  | "grid"
  | "chat"
  | "list"
  | "user"
  | "search"
  | "cart"
  | "send"
  | "smile"
  | "chef"
  | "plus";

function Icon({
  name,
  size = 24,
  strokeWidth = 1.8,
}: {
  name: IconName;
  size?: number;
  strokeWidth?: number;
}) {
  const paths: Record<IconName, ReactNode> = {
    home: (
      <>
        <path d="m3 10.8 9-7.3 9 7.3" />
        <path d="M5.5 9.7v10.8h13V9.7M9.2 20.5v-6.2h5.6v6.2" />
      </>
    ),
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1.4" />
        <rect x="14" y="3" width="7" height="7" rx="1.4" />
        <rect x="3" y="14" width="7" height="7" rx="1.4" />
        <rect x="14" y="14" width="7" height="7" rx="1.4" />
      </>
    ),
    chat: (
      <>
        <path d="M20.3 15.5A8.8 8.8 0 0 0 21 12c0-5-4-9-9-9s-9 4-9 9 4 9 9 9a9 9 0 0 0 4.2-1.1L21 21l-.7-5.5Z" />
        <path d="M8 12h.01M12 12h.01M16 12h.01" strokeWidth="2.8" />
      </>
    ),
    list: (
      <>
        <path d="M9 6h12M9 12h12M9 18h12" />
        <path d="M3.5 6h.01M3.5 12h.01M3.5 18h.01" strokeWidth="3.2" />
      </>
    ),
    user: (
      <>
        <circle cx="12" cy="8" r="4" />
        <path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
      </>
    ),
    search: (
      <>
        <circle cx="10.7" cy="10.7" r="6.7" />
        <path d="m16 16 4.5 4.5" />
      </>
    ),
    cart: (
      <>
        <path d="M3 4h2l2.2 10.2a2 2 0 0 0 2 1.6h7.9a2 2 0 0 0 1.9-1.5L20.5 8H6" />
        <circle cx="9.5" cy="20" r="1" fill="currentColor" stroke="none" />
        <circle cx="17.5" cy="20" r="1" fill="currentColor" stroke="none" />
      </>
    ),
    send: (
      <>
        <path d="m21 3-7.5 18-3.2-7.3L3 10.5 21 3Z" />
        <path d="m10.3 13.7 4.5-4.5" />
      </>
    ),
    smile: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M8 14.5a5 5 0 0 0 8 0M9 9h.01M15 9h.01" />
      </>
    ),
    chef: (
      <>
        <path d="M7 10.5a4 4 0 0 1 .7-7.9A4.8 4.8 0 0 1 12 1a4.8 4.8 0 0 1 4.3 1.6 4 4 0 0 1 .7 7.9V20H7v-9.5Z" />
        <path d="M7 14h10" />
      </>
    ),
    plus: (
      <>
        <path d="M12 5v14M5 12h14" />
      </>
    ),
  };

  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={strokeWidth}
    >
      {paths[name]}
    </svg>
  );
}

const products = [
  {
    id: 1,
    name: "Spaghetti di grano duro",
    detail: "La Molisana · 500 g",
    price: "1,25 €",
    image:
      "https://images.unsplash.com/photo-1551462147-ff29053bfc14?auto=format&fit=crop&w=700&q=90",
    alt: "Uncooked spaghetti on a light kitchen surface",
    color: "bg-[#f4eee1]",
  },
  {
    id: 2,
    name: "Pomodoro e basilico",
    detail: "Bio Orto · 350 g",
    price: "2,10 €",
    image:
      "https://images.unsplash.com/photo-1607863680026-e113604ccb17?auto=format&fit=crop&w=700&q=90",
    alt: "Fresh tomato on a bright yellow surface",
    color: "bg-[#f8de66]",
  },
];

const navItems: { name: IconName; label: string }[] = [
  { name: "home", label: "Inicio" },
  { name: "grid", label: "Categorías" },
  { name: "chat", label: "Chat" },
  { name: "list", label: "Listas" },
  { name: "user", label: "Cuenta" },
];

function ProductCard({
  product,
  onAdd,
  added,
}: {
  product: (typeof products)[number];
  onAdd: () => void;
  added: boolean;
}) {
  return (
    <article className="group flex min-w-0 flex-col overflow-hidden rounded-[24px] border border-black/6 bg-white shadow-[0_8px_30px_rgba(28,52,42,0.07)]">
      <div className={`relative h-40 overflow-hidden sm:h-48 ${product.color}`}>
        <img
          className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
          src={product.image}
          alt={product.alt}
        />
        <span className="absolute left-3 top-3 rounded-full bg-white/90 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.12em] text-[#087a50] backdrop-blur">
          Elección de Merche
        </span>
      </div>
      <div className="flex flex-1 flex-col p-4 sm:p-5">
        <h3 className="text-[17px] font-bold leading-tight text-[#15231d]">
          {product.name}
        </h3>
        <p className="mt-1 text-sm text-[#708078]">{product.detail}</p>
        <div className="mt-4 flex items-center justify-between gap-3">
          <strong className="text-xl tracking-tight text-[#13231c]">
            {product.price}
          </strong>
          <button
            className={`flex h-11 items-center gap-2 rounded-full px-4 text-sm font-bold text-white transition active:scale-95 ${
              added
                ? "bg-[#183e31]"
                : "bg-[#00a86b] hover:bg-[#008f5b]"
            }`}
            type="button"
            onClick={onAdd}
          >
            <Icon name={added ? "plus" : "cart"} size={19} />
            {added ? "Añadido" : "Añadir"}
          </button>
        </div>
      </div>
    </article>
  );
}

export default function App() {
  const [message, setMessage] = useState("");
  const [active, setActive] = useState("Chat");
  const [added, setAdded] = useState<number[]>([]);
  const [extraMessage, setExtraMessage] = useState("");
  const [notice, setNotice] = useState("");

  function showNotice(text: string) {
    setNotice(text);
    window.setTimeout(() => setNotice(""), 2200);
  }

  function addProduct(id: number) {
    setAdded((items) =>
      items.includes(id) ? items.filter((item) => item !== id) : [...items, id],
    );
    showNotice(
      added.includes(id)
        ? "Producto eliminado de tu lista"
        : "Producto añadido a tu lista",
    );
  }

  function sendMessage(event: FormEvent) {
    event.preventDefault();
    if (!message.trim()) return;
    setExtraMessage(message.trim());
    setMessage("");
  }

  return (
    <div className="min-h-screen bg-[#f7faf8] text-[#15231d]">
      <div className="mx-auto flex min-h-screen max-w-[1120px] flex-col bg-white shadow-[0_0_80px_rgba(27,62,49,0.08)]">
        <header className="px-5 pb-4 pt-7 sm:px-9 sm:pt-9 lg:px-12">
          <h1 className="text-[30px] font-extrabold leading-none tracking-[-0.05em] sm:text-[38px]">
            Merche
          </h1>
          <p className="mt-1.5 text-sm font-medium text-[#7b8781] sm:text-base">
            Planifica tus comidas y llena el carrito en un momento
          </p>
        </header>

        <main className="flex-1 px-5 pb-48 sm:px-9 lg:px-12">
          <section aria-label="Conversación con Merche" className="pt-5">
            <div className="ml-auto flex max-w-[650px] items-end justify-end gap-3">
              <div>
                <div className="rounded-[25px] rounded-br-[8px] bg-[#00a86b] px-5 py-4 text-[17px] leading-relaxed text-white shadow-[0_10px_25px_rgba(0,168,107,0.18)] sm:text-lg">
                  Necesito ideas para una cena con pasta para 4 personas
                </div>
                <p className="mr-1 mt-1.5 text-right text-xs font-medium text-[#7b8781]">
                  9:41
                </p>
              </div>
            </div>

            <div className="mt-4 flex max-w-[720px] items-start gap-3">
              <div className="mt-1 grid h-11 w-11 shrink-0 place-items-center rounded-[15px] bg-[#00a86b] text-white shadow-[0_7px_18px_rgba(0,168,107,0.2)]">
                <Icon name="chat" size={23} strokeWidth={2.2} />
              </div>
              <div>
                <div className="rounded-[25px] rounded-tl-[8px] bg-[#f0f3f1] px-5 py-4 text-[17px] leading-relaxed sm:text-lg">
                  ¡Claro! Una pasta al pomodoro siempre funciona. Te dejo mis
                  dos básicos favoritos para una cena deliciosa.
                </div>
                <p className="ml-2 mt-1.5 text-xs font-medium text-[#7b8781]">
                  Merche · ahora
                </p>
              </div>
            </div>

            {extraMessage && (
              <div className="ml-auto mt-4 max-w-[620px]">
                <div className="rounded-[25px] rounded-br-[8px] bg-[#183e31] px-5 py-4 text-[17px] text-white">
                  {extraMessage}
                </div>
                <p className="mr-1 mt-1.5 text-right text-xs text-[#7b8781]">
                  ahora
                </p>
              </div>
            )}
          </section>

          <section className="ml-auto mt-5 max-w-[960px]">
            <div className="grid grid-cols-1 gap-3 min-[520px]:grid-cols-2 sm:gap-4">
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  added={added.includes(product.id)}
                  onAdd={() => addProduct(product.id)}
                />
              ))}
            </div>

            <div className="mt-4 flex flex-wrap gap-2.5">
              <button
                type="button"
                onClick={() => {
                  setAdded([1, 2]);
                  showNotice("Ingredientes añadidos a tu lista");
                }}
                className="flex h-12 flex-1 items-center justify-center gap-2 rounded-full border-[1.5px] border-[#00a86b] px-5 text-sm font-bold text-[#00a86b] transition hover:bg-[#effaf5] sm:flex-none"
              >
                <Icon name="list" size={20} />
                Añadir todo
              </button>
              <button
                type="button"
                onClick={() => showNotice("Buscando otra receta para ti…")}
                className="flex h-12 flex-1 items-center justify-center gap-2 rounded-full border-[1.5px] border-[#00a86b] px-5 text-sm font-bold text-[#00a86b] transition hover:bg-[#effaf5] sm:flex-none"
              >
                <Icon name="chef" size={20} />
                Ver otra receta
              </button>
            </div>
          </section>
        </main>

        <div className="fixed inset-x-0 bottom-[90px] z-20 mx-auto max-w-[1120px] px-4 sm:bottom-[96px] sm:px-9 lg:px-12">
          <form
            onSubmit={sendMessage}
            className="flex h-[62px] items-center gap-3 rounded-[23px] border border-black/5 bg-[#f2f5f3]/95 px-4 shadow-[0_10px_35px_rgba(24,62,49,0.13)] backdrop-blur"
          >
            <span className="text-[#718078]">
              <Icon name="search" size={24} />
            </span>
            <input
              className="min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-[#89938e]"
              placeholder="Busca un producto o pídele a Merche un menú, una receta…"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
            />
            <button
              aria-label="Enviar a Merche"
              className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[#00a86b] text-white shadow-[0_7px_18px_rgba(0,168,107,0.25)] transition hover:bg-[#008f5b] active:scale-95"
              type="submit"
            >
              <Icon name="send" size={21} strokeWidth={2.1} />
            </button>
          </form>
        </div>

        <nav className="fixed inset-x-0 bottom-0 z-30 mx-auto h-[76px] max-w-[1120px] border-t border-black/5 bg-white/95 px-2 backdrop-blur sm:h-[82px]">
          <div className="mx-auto flex h-full max-w-[850px] items-center justify-between">
            {navItems.map((item) => {
              const isActive = active === item.label;
              return (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => setActive(item.label)}
                  className={`relative flex h-[62px] min-w-[60px] flex-col items-center justify-center gap-1 rounded-[20px] px-3 text-[11px] font-semibold transition sm:min-w-[90px] sm:text-xs ${
                    isActive
                      ? "bg-[#e2f7ed] text-[#00a86b]"
                      : "text-[#6f7c76] hover:bg-[#f3f6f4]"
                  }`}
                >
                  {item.label === "Listas" && added.length > 0 && (
                    <span className="absolute right-3 top-1.5 grid h-5 min-w-5 place-items-center rounded-full bg-[#183e31] px-1 text-[10px] text-white">
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
            className="fixed left-1/2 top-5 z-50 -translate-x-1/2 rounded-full bg-[#183e31] px-5 py-3 text-sm font-semibold text-white shadow-xl"
          >
            {notice}
          </div>
        )}
      </div>
    </div>
  );
}
