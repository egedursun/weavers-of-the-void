import { DOMAIN_GLYPH, DOMAIN_GLYPH_FALLBACK } from './domainGlyphIcons'

export function DomainGlyph({ domain }: { domain: string }) {
  const Icon =
    DOMAIN_GLYPH[domain as keyof typeof DOMAIN_GLYPH] ?? DOMAIN_GLYPH_FALLBACK
  return (
    <span
      data-domain='domain-glyph'
      className='inline-flex shrink-0 items-center justify-center text-primary'
    >
      <Icon aria-hidden='true' className='size-icon-sm' />
    </span>
  )
}
