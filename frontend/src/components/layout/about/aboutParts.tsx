import { type ReactNode } from 'react'
import { type LucideIcon } from 'lucide-react'
import { Label, SectionTitle } from '@/components/typography'

export function SectionHeading({
  id,
  icon: Icon,
  eyebrow,
  title,
  aside,
}: {
  id: string
  icon: LucideIcon
  eyebrow: string
  title: string
  aside?: ReactNode
}) {
  return (
    <div className='flex flex-wrap items-end justify-between gap-3'>
      <div className='flex items-center gap-3'>
        <span className='flex size-10 shrink-0 items-center justify-center rounded-lg border border-brand-gold/40 bg-brand-gold/10 text-brand-gold'>
          <Icon className='size-icon-md' aria-hidden />
        </span>
        <div className='flex flex-col'>
          <Label variant='overline' className='text-brand-gold'>
            {eyebrow}
          </Label>
          <SectionTitle id={id}>{title}</SectionTitle>
        </div>
      </div>
      {aside}
    </div>
  )
}
