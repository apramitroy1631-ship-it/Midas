/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend URL baked in at build time (e.g. the Railway URL on Vercel). When set,
   * the sign-in screen doesn't ask for it. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
