import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/api': process.env.JEVSCOUT_API_ORIGIN || 'http://127.0.0.1:8000'
    }
  }
});
