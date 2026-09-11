import type { Connection } from "./types";

/**
 * Saved tenant connections.
 *
 * API keys live in this browser only — the console is a client of the API, not
 * a second place that owns tenant credentials. Clearing site data logs you out
 * of every tenant, which is the intended behaviour on a shared machine.
 */
const KEY = "buildx.connections";
const ACTIVE = "buildx.active";
const THEME = "buildx.theme";

const PALETTE = ["#6ea8fe", "#b98cff", "#4ade80", "#fbbf24", "#f87171", "#38bdf8"];

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* private mode or blocked storage — the session still works, it just won't persist */
  }
}

export const store = {
  connections: (): Connection[] => read<Connection[]>(KEY, []),

  save(conn: Omit<Connection, "id" | "color"> & { id?: string; color?: string }): Connection {
    const list = store.connections();
    const id = conn.id ?? crypto.randomUUID();
    const existing = list.findIndex((c) => c.id === id);
    const full: Connection = {
      id,
      label: conn.label,
      apiKey: conn.apiKey,
      baseUrl: conn.baseUrl,
      color: conn.color ?? PALETTE[list.length % PALETTE.length],
    };
    if (existing >= 0) list[existing] = full;
    else list.push(full);
    write(KEY, list);
    return full;
  },

  remove(id: string): void {
    write(KEY, store.connections().filter((c) => c.id !== id));
    if (store.activeId() === id) store.setActive(store.connections()[0]?.id ?? null);
  },

  activeId: (): string | null => read<string | null>(ACTIVE, null),
  setActive: (id: string | null) => write(ACTIVE, id),

  active(): Connection | null {
    const list = store.connections();
    const id = store.activeId();
    return list.find((c) => c.id === id) ?? list[0] ?? null;
  },

  theme: (): "dark" | "light" => read<"dark" | "light">(THEME, "dark"),
  setTheme: (t: "dark" | "light") => write(THEME, t),
};
