import { type ReactNode } from 'react'
import { BookOpenText } from 'lucide-react'
import { Muted } from '@/components/typography'
import { Medallion } from './KpiTile'

export function IntroNote({ children }: { children: ReactNode }) {
  return (
    <div
      data-domain='intro-note'
      className='flex min-w-0 items-center gap-3 rounded-md border surface-sheen border-gild/60 bg-card px-4 py-3'
    >
      <Medallion icon={BookOpenText} tone='gold' size='sm' />
      <Muted className='min-w-0 flex-1'>{children}</Muted>
    </div>
  )
}
