/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE: string;
  readonly VITE_UI_REQUIRE_AUTH: string;
  readonly VITE_INTERNAL_TOKEN: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
