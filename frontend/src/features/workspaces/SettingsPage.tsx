import { type ReactNode } from 'react'
import { Link } from '@tanstack/react-router'
import { ArrowLeft, LibraryBig } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Divider } from '@/components/ui/ornate'
import { Medallion } from '@/components/domain'
import { ThemeSwitch } from '@/components/layout/ThemeSwitch'
import { Muted, PageTitle, Text } from '@/components/typography'
import { AccountMenu } from '@/features/accounts/AccountMenu'

export function SettingsPage({
  title,
  lead,
  crest,
  children,
}: {
  title: string
  lead: string
  crest: ReactNode
  children: ReactNode
}) {
  return (
    <main
      id='content'
      data-domain='team-settings'
      className='relative flex min-h-svh flex-col items-center gap-6 overflow-x-clip bg-background px-4 py-6 sm:py-10'
    >
      <span
        aria-hidden='true'
        className='pointer-events-none absolute inset-x-0 top-0 h-160 bg-linear-to-b from-brand-violet/12 via-primary/5 to-transparent'
      />
      <nav
        aria-label='Leave the settings'
        className='relative flex w-full max-w-6xl min-w-0 flex-wrap items-center justify-between gap-3'
      >
        <Button asChild variant='outline' size='tile' className='w-auto'>
          <Link to='/' aria-label='Back to the Library of Universes'>
            <ArrowLeft aria-hidden='true' className='text-muted-foreground' />
            <Medallion icon={LibraryBig} tone='gold' size='sm' />
            <span className='flex min-w-0 flex-col'>
              <Text as='span' weight='semibold' className='font-display'>
                The Library of Universes
              </Text>
              <Muted as='span' variant='caption'>
                Back to your shelves
              </Muted>
            </span>
          </Link>
        </Button>
        <span className='flex items-center gap-0.5 rounded-md border surface-sheen border-gild/70 bg-card px-1.5 py-0.5'>
          <ThemeSwitch />
          <AccountMenu />
        </span>
      </nav>
      <header className='relative flex w-full max-w-6xl min-w-0 flex-col items-center gap-3 text-center'>
        {crest}
        <div className='flex min-w-0 flex-col items-center gap-1'>
          <PageTitle className='text-gilded'>{title}</PageTitle>
          <Divider className='w-56' />
        </div>
        <Muted variant='prose'>{lead}</Muted>
      </header>
      <div className='relative flex w-full max-w-6xl min-w-0 flex-col gap-6'>
        {children}
      </div>
    </main>
  )
}
