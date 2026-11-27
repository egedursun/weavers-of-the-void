import type { APIRoute } from 'astro'
import { LOCALES, page } from '../i18n'
import { expansionsFor } from '../data/expansions'
import { siteUrl } from '../seo'

function escaped(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

export const GET: APIRoute = ({ site }) => {
  const origin = siteUrl(site)
  const paths = ['', 'expansions', 'services', ...expansionsFor('en').map((item) => `expansions/${item.slug}`)]
  const entries = paths.flatMap((path) => {
    const alternates = [
      ...LOCALES.map((other) => `<xhtml:link rel="alternate" hreflang="${other}" href="${escaped(`${origin}${page(other, path)}`)}"/>`),
      `<xhtml:link rel="alternate" hreflang="x-default" href="${escaped(`${origin}${page('en', path)}`)}"/>`,
    ].join('')
    return LOCALES.map((locale) => `<url><loc>${escaped(`${origin}${page(locale, path)}`)}</loc>${alternates}</url>`)
  })
  const body =
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' +
    entries.join('\n') +
    '\n</urlset>\n'
  return new Response(body, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } })
}
