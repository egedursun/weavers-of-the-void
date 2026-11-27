import { APP_NAME } from '@/config/brand'
import { Muted, PageTitle } from '@/components/typography'
import { Logo } from './Logo'

type SplashScreenProps = {
  title?: string
  line: string
}

export function SplashScreen({
  title = `${APP_NAME}®`,
  line,
}: SplashScreenProps) {
  return (
    <main
      id='content'
      role='status'
      aria-busy='true'
      aria-label={line}
      className='flex min-h-svh flex-col items-center justify-center gap-6 bg-background px-4 text-center'
    >
      <span className='relative flex size-28 items-center justify-center'>
        <span
          aria-hidden='true'
          className='absolute inset-0 animate-breathe rounded-full bg-primary/20 blur-xl motion-reduce:animate-none'
        />
        <Logo size='boot' className='relative size-full' title={APP_NAME} />
      </span>
      <span className='flex flex-col items-center gap-2'>
        <PageTitle className='text-gilded font-brand'>{title}</PageTitle>
        <Muted>{line}</Muted>
      </span>
      <span
        aria-hidden='true'
        className='relative h-0.5 w-40 overflow-hidden rounded-full bg-muted'
      >
        <span className='absolute inset-y-0 left-0 w-1/3 animate-indeterminate rounded-full bg-primary motion-reduce:animate-none' />
      </span>
    </main>
  )
}
