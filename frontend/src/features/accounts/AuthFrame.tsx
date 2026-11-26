import { type ReactNode } from 'react'
import { APP_NAME, APP_SUBTITLE, APP_VERSION } from '@/config/brand'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Divider } from '@/components/ui/ornate'
import { Section } from '@/components/domain'
import { Logo } from '@/components/layout/Logo'
import { ThemeSwitch } from '@/components/layout/ThemeSwitch'
import { Label, Muted, PageTitle } from '@/components/typography'

export function AuthFrame({
  title,
  icon,
  heading,
  lead,
  children,
  footer = null,
  wide = false,
}: {
  title: string
  icon: LucideIcon
  heading: string
  lead: string
  children: ReactNode
  footer?: ReactNode
  wide?: boolean
}) {
  const width = wide ? 'max-w-4xl' : 'max-w-md'
  return (
    <main
      id='content'
      data-domain='auth'
      className='relative flex min-h-svh flex-col items-center gap-6 overflow-x-clip bg-background px-4 py-8 sm:py-14'
    >
      <span
        aria-hidden='true'
        className='pointer-events-none absolute inset-x-0 top-0 h-160 bg-linear-to-b from-brand-violet/14 via-primary/6 to-transparent'
      />
      <div className={cn('relative flex w-full min-w-0 justify-end', width)}>
        <span className='flex items-center rounded-md border surface-sheen border-gild/70 bg-card px-1.5 py-0.5'>
          <ThemeSwitch />
        </span>
      </div>
      <header
        className={cn(
          'relative flex w-full min-w-0 flex-col items-center gap-3 text-center',
          width
        )}
      >
        <span className='relative flex items-center justify-center'>
          <span
            aria-hidden='true'
            className='absolute inset-3 rounded-full bg-linear-to-br from-primary/35 via-brand-violet/30 to-brand-magenta/25 blur-2xl'
          />
          <span className='relative flex size-portrait-2xl items-center justify-center'>
            <Logo
              size='md'
              className='size-full drop-shadow-xl'
              title={APP_NAME}
            />
          </span>
        </span>
        <div className='flex min-w-0 flex-wrap items-center justify-center gap-2'>
          <Label variant='overline'>{APP_NAME}</Label>
          <Badge variant='outline' size='sm' className='font-mono'>
            {`v${APP_VERSION}`}
          </Badge>
        </div>
        <div className='flex min-w-0 flex-col items-center gap-1'>
          <PageTitle className='text-gilded'>{heading}</PageTitle>
          <Divider className='w-56' />
        </div>
        <Muted variant='prose'>{lead}</Muted>
      </header>
      <div className={cn('relative flex w-full min-w-0 flex-col gap-4', width)}>
        <Section title={title} icon={icon} surface='card'>
          {children}
        </Section>
        {footer}
        <Muted variant='caption' className='text-center'>
          {APP_SUBTITLE}
        </Muted>
      </div>
    </main>
  )
}
