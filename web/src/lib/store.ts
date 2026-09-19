import type { Connection } from "./types";

/**
 * Saved tenant connections.
 *
 * API keys live in this browser only — the console is a client of the API, not
 * a second place that owns tenant credentials.
 *
 * By default a sign-in lasts only as long as the tab/browser session
 * (sessionStorage): opening the app link again later asks you to sign in
 * rather than dropping you into someone's still-open session. "Keep me signed
 * in" (opt-in at sign-in) moves credentials to localStorage instead. Theme and
 * layout prefs are not credentials and always persist.
 */
const KEY = "buildx.connections";
const ACTIVE = "buildx.active";
const THEME = "buildx.theme";
const SIDEBAR_COLLAPSED = "buildx.sidebarCollapsed";
const REMEMBER = "buildx.remember";

const PALETTE = ["#6ea8fe", "#b98cff", "#4ade80", "#fbbf24", "#f87171", "#38bdf8"];

function remembered(): boolean {
  try {
    return localStorage.getItem(REMEMBER) === "1";
  } catch {
    return false;
  }
}

/** Where credentials live right now: durable only if the user opted in. */
function authStorage(): Storage {
  return remembered() ? localStorage : sessionStorage;
}

// Sessions persisted by earlier versions (before this was opt-in) would
// otherwise keep silently signing people in. Drop them unless opted in.
try {
  if (!remembered()) {
    localStorage.removeItem(KEY);
    localStorage.removeItem(ACTIVE);
  }
} catch {
  /* blocked storage — nothing to clean up */
}

function read<T>(key: string, fallback: T, storage: Storage = localStorage): T {
  try {
    const raw = storage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown, storage: Storage = localStorage): void {
  try {
    storage.setItem(key, JSON.stringify(value));
  } catch {
    /* private mode or blocked storage — the session still works, it just won't persist */
  }
}

export const store = {
  /** Call before saving a connection: true = keep signed in across visits. */
  setRemember(remember: boolean): void {
    try {
      if (remember) {
        localStorage.setItem(REMEMBER, "1");
      } else {
        localStorage.removeItem(REMEMBER);
        localStorage.removeItem(KEY);
        localStorage.removeItem(ACTIVE);
      }
    } catch {
      /* blocked storage */
    }
  },

  connections: (): Connection[] => read<Connection[]>(KEY, [], authStorage()),

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
      userEmail: conn.userEmail,
      role: conn.role,
    };
    if (existing >= 0) list[existing] = full;
    else list.push(full);
    write(KEY, list, authStorage());
    return full;
  },

  remove(id: string): void {
    write(KEY, store.connections().filter((c) => c.id !== id), authStorage());
    if (store.activeId() === id) store.setActive(store.connections()[0]?.id ?? null);
  },

  activeId: (): string | null => read<string | null>(ACTIVE, null, authStorage()),
  setActive: (id: string | null) => write(ACTIVE, id, authStorage()),

  active(): Connection | null {
    const list = store.connections();
    const id = store.activeId();
    return list.find((c) => c.id === id) ?? list[0] ?? null;
  },

  theme: (): "dark" | "light" => read<"dark" | "light">(THEME, "dark"),
  setTheme: (t: "dark" | "light") => write(THEME, t),

  sidebarCollapsed: (): boolean => read<boolean>(SIDEBAR_COLLAPSED, false),
  setSidebarCollapsed: (v: boolean) => write(SIDEBAR_COLLAPSED, v),
};
