import { type ReactNode } from 'react'
import { OrnateFrame } from '@/components/ui/ornate'

export function HeroFrame({ children }: { children: ReactNode }) {
  return (
    <OrnateFrame
      data-domain='hero-frame'
      crest
      footCrest
      className='flex min-w-0 flex-col gap-4 px-6 py-9 sm:px-8'
    >
      {children}
    </OrnateFrame>
  )
}
