import { Logo } from '@/components/layout/Logo'
import { Muted, PageTitle } from '@/components/typography'

export function EnteringUniverse() {
  return (
    <main
      id='content'
      role='status'
      aria-busy='true'
      className='flex min-h-svh flex-col items-center justify-center gap-4 bg-background px-4 text-center'
    >
      <span className='relative flex h-28 w-28 items-center justify-center'>
        <span
          aria-hidden='true'
          className='absolute inset-0 animate-ping rounded-full bg-primary/15 motion-reduce:animate-none'
        />
        <Logo size='md' className='size-full' />
      </span>
      <PageTitle className='text-gilded'>Entering the universe</PageTitle>
      <Muted>Its book is being opened.</Muted>
    </main>
  )
}
