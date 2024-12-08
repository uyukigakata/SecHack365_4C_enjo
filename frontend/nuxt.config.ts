// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  app: {
    head: {
      charset: 'utf-8',
      viewport: 'width=device-width, initial-scale=1',
    }
  },
  modules: ['@nuxtjs/tailwindcss', '@nuxtjs/google-fonts'],
  compatibilityDate: '2024-11-01',
  devtools: { enabled: true },
  css: ['~/assets/css/root.css'],
  googleFonts: {
    families: {
      'Noto+Sans+JP': true
    }
  },
  ssr: false,
})