import { en, type Copy } from './en'
import { tr } from './tr'

export const LOCALES = ['en', 'tr'] as const
export type Locale = (typeof LOCALES)[number]

export const LOCALE_NAMES: Record<Locale, string> = { en: 'English', tr: 'Türkçe' }
export const LOCALE_TAGS: Record<Locale, string> = { en: 'en_US', tr: 'tr_TR' }

const COPY: Record<Locale, Copy> = { en, tr }

export const REPOSITORY = 'https://github.com/egedursun/weavers-of-the-void'
export const COMMUNITY = 'https://github.com/egedursun/weavers-of-the-void/discussions'
export const FORM_ENDPOINT = 'https://formsubmit.co/ajax/edogandursun@gmail.com'

export function copyFor(locale: Locale): Copy {
  return COPY[locale]
}

export function isLocale(value: string | undefined): value is Locale {
  return LOCALES.some((locale) => locale === value)
}

export function asset(path: string): string {
  return `${import.meta.env.BASE_URL.replace(/\/$/, '')}/${path.replace(/^\//, '')}`
}

export function page(locale: Locale, path = ''): string {
  const tail = path.replace(/^\/|\/$/g, '')
  return asset(tail ? `${locale}/${tail}/` : `${locale}/`)
}

export function repositoryFile(name: string): string {
  return `${REPOSITORY}/blob/main/${name}`
}
