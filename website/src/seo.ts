import { REPOSITORY, asset, page, repositoryFile, type Locale } from './i18n'

export const APP_NAME = 'Weavers of the Void'
export const SHARE_CARD = { width: 1200, height: 630, type: 'image/jpeg' } as const
export const THEME_COLOR = '#110b1f'

export type ShareImage = { path: string; alt: string }

export type Crumb = { name: string; path: string }

type Node = Record<string, unknown>

export function siteUrl(site: URL | undefined): string {
  return site?.toString().replace(/\/$/, '') ?? ''
}

export function shareCardOf(locale: Locale): string {
  return `social/${locale}.jpg`
}

export function expansionCardOf(cover: number): string {
  return `social/expansions/${cover}.jpg`
}

function organization(origin: string): Node {
  return {
    '@type': 'Organization',
    '@id': `${origin}${asset('')}#organization`,
    name: APP_NAME,
    url: `${origin}${asset('')}`,
    logo: `${origin}${asset('brand/logo-512.png')}`,
    sameAs: [REPOSITORY],
  }
}

function website(origin: string, locale: Locale): Node {
  return {
    '@type': 'WebSite',
    '@id': `${origin}${page(locale)}#website`,
    name: APP_NAME,
    url: `${origin}${page(locale)}`,
    inLanguage: locale,
    publisher: { '@id': `${origin}${asset('')}#organization` },
  }
}

export function baseGraph(origin: string, locale: Locale): Node[] {
  return [organization(origin), website(origin, locale)]
}

export function softwareGraph(origin: string, locale: Locale, description: string): Node {
  return {
    '@type': 'SoftwareApplication',
    name: APP_NAME,
    description,
    url: `${origin}${page(locale)}`,
    image: `${origin}${asset(shareCardOf(locale))}`,
    applicationCategory: 'GameApplication',
    applicationSubCategory: 'Worldbuilding',
    operatingSystem: 'Windows, macOS, Linux',
    inLanguage: locale,
    isAccessibleForFree: true,
    license: repositoryFile('LICENSING.md'),
    downloadUrl: REPOSITORY,
    offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
    publisher: { '@id': `${origin}${asset('')}#organization` },
  }
}

export function faqGraph(items: { q: string; a: string }[]): Node {
  return {
    '@type': 'FAQPage',
    mainEntity: items.map((item) => ({
      '@type': 'Question',
      name: item.q,
      acceptedAnswer: { '@type': 'Answer', text: item.a },
    })),
  }
}

export function breadcrumbGraph(origin: string, locale: Locale, trail: Crumb[]): Node {
  return {
    '@type': 'BreadcrumbList',
    itemListElement: [{ name: APP_NAME, path: '' }, ...trail].map((crumb, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: crumb.name,
      item: `${origin}${page(locale, crumb.path)}`,
    })),
  }
}

export function itemListGraph(origin: string, locale: Locale, items: Crumb[]): Node {
  return {
    '@type': 'ItemList',
    numberOfItems: items.length,
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      url: `${origin}${page(locale, item.path)}`,
    })),
  }
}

export function structuredData(graph: Node[]): string {
  return JSON.stringify({ '@context': 'https://schema.org', '@graph': graph }).replace(/</g, '\\u003c')
}
