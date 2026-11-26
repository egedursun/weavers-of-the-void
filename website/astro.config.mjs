import { defineConfig } from 'astro/config'

export default defineConfig({
  site: 'https://egedursun.github.io',
  base: '/weavers-of-the-void',
  trailingSlash: 'always',
  output: 'static',
  devToolbar: { enabled: false },
  scopedStyleStrategy: 'class',
  i18n: {
    locales: ['en', 'tr'],
    defaultLocale: 'en',
    routing: { prefixDefaultLocale: true, redirectToDefaultLocale: false },
  },
  build: { format: 'directory' },
})
