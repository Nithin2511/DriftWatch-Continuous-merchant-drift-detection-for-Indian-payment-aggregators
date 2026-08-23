import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // GitHub Pages serves a project site from https://<user>.github.io/<repo>/, so every
  // asset URL needs that prefix or the page loads with a blank screen and 404s on its
  // own JS. BASE_PATH is injected by .github/workflows/deploy.yml from the repository
  // name, so renaming the repo does not break the deploy. Local dev and `vite preview`
  // leave it unset and serve from '/'.
  base: process.env.BASE_PATH || '/',

  server: {
    port: 3000,
    open: true,
  },
});
