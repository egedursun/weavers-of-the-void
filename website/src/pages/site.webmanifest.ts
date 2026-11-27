import type { APIRoute } from 'astro'
import { asset, page } from '../i18n'
import { APP_NAME, THEME_COLOR } from '../seo'

export const GET: APIRoute = () => {
  const manifest = {
    name: APP_NAME,
    short_name: APP_NAME,
    description: 'The universe simulator that writes its own history. Open source and free forever.',
    lang: 'en',
    start_url: page('en'),
    scope: asset(''),
    display: 'browser',
    background_color: THEME_COLOR,
    theme_color: THEME_COLOR,
    icons: [
      { src: asset('brand/logo-192.png'), sizes: '192x192', type: 'image/png' },
      { src: asset('brand/logo-512.png'), sizes: '512x512', type: 'image/png' },
    ],
  }
  return new Response(JSON.stringify(manifest, null, 2), { headers: { 'Content-Type': 'application/manifest+json' } })
}
