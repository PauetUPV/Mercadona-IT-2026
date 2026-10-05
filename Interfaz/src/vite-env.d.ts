/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Backend base URL, e.g. http://localhost:8000. Unset = built-in fake backend.
  readonly VITE_API_URL?: string;
}
