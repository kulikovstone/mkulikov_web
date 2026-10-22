import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

export default defineConfig({
  build: {
    rolldownOptions: {
      input: {
        home: fileURLToPath(new URL('./index.html', import.meta.url)),
        experience: fileURLToPath(new URL('./experience/index.html', import.meta.url)),
        experienceRu: fileURLToPath(new URL('./experience/ru/index.html', import.meta.url)),
      },
    },
  },
})
