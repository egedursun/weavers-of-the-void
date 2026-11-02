import { type ReactNode } from 'react'
import { Label } from '@/components/typography'

type SpecimenProps = {
  name: string
  children: ReactNode
}

export function Specimen({ name, children }: SpecimenProps) {
  return (
    <div
      data-specimen={name}
      className='grid min-w-0 grid-cols-1 items-start gap-x-6 gap-y-2 border-t pt-4 md:grid-cols-label-track'
    >
      <Label variant='overline' truncate>
        {name}
      </Label>
      <div className='flex min-w-0 flex-col gap-3'>{children}</div>
    </div>
  )
}

export function Row({ children }: { children: ReactNode }) {
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2'>{children}</div>
  )
}
