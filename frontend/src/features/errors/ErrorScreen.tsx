import { type ReactNode } from 'react'
import { APP_NAME } from '@/config/brand'
import { type LucideIcon } from 'lucide-react'
import { Medallion } from '@/components/domain'
import { Logo } from '@/components/layout/Logo'
import { Label, Muted, PageTitle, Text } from '@/components/typography'

type ErrorScreenProps = {
  code: string
  icon: LucideIcon
  title: string
  description: string
  action?: ReactNode
}

export function ErrorScreen({
  code,
  icon,
  title,
  description,
  action,
}: ErrorScreenProps) {
  return (
    <main
      id='content'
      className='relative flex min-h-svh flex-col items-center justify-center gap-8 overflow-hidden bg-background px-4 py-12 text-center'
    >
      <span
        aria-hidden='true'
        className='pointer-events-none absolute inset-x-0 top-0 h-160 bg-linear-to-b from-brand-violet/12 via-primary/5 to-transparent'
      />
      <div className='relative flex flex-col items-center gap-2'>
        <span className='relative flex h-28 w-28 items-center justify-center'>
          <span
            aria-hidden='true'
            className='absolute inset-2 rounded-full bg-linear-to-br from-primary/30 via-brand-violet/25 to-brand-magenta/20 blur-xl'
          />
          <Logo size='md' className='relative size-full opacity-90' />
        </span>
        <Text as='span' weight='semibold' className='font-brand text-primary'>
          {APP_NAME}
        </Text>
      </div>
      <section className='relative flex w-full max-w-lg min-w-0 flex-col items-center gap-4 rounded-xl border bg-card p-8 shadow-lg'>
        <Medallion icon={icon} tone='warning' />
        <Label variant='overline'>{`Error ${code}`}</Label>
        <PageTitle>{title}</PageTitle>
        <Muted variant='prose'>{description}</Muted>
        {action && (
          <div className='flex flex-wrap justify-center gap-2 pt-2'>
            {action}
          </div>
        )}
      </section>
    </main>
  )
}
