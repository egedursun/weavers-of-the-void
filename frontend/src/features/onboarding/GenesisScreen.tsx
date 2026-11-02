import { Link, useNavigate } from '@tanstack/react-router'
import { APP_NAME, APP_SUBTITLE } from '@/config/brand'
import { useEvent } from '@/realtime'
import {
  ArchiveRestore,
  ArrowLeft,
  ChevronDown,
  CircleAlert,
  CircleCheck,
  Globe,
  LoaderCircle,
} from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, JobProgress } from '@/components/domain'
import { Logo } from '@/components/layout/Logo'
import { Label, Muted, PageTitle, Text } from '@/components/typography'
import { BackupsPanel } from '@/features/backups/BackupsPanel'
import { ShareWorld } from '@/features/backups/ShareWorld'
import { useRecentJobs } from '@/features/epoch/api'
import { FeedCollector } from '@/features/feed/FeedCollector'
import { useFeed } from '@/features/feed/feedStore'
import { useWorldState } from '@/features/overview/api'
import { useRevealQueue } from '@/features/pantheon/revealStore'
import { GenesisWizard } from './GenesisWizard'

function GenesisProgress() {
  const jobs = useRecentJobs()
  const lines = useFeed((state) => state.lines)
  const job = (jobs.data ?? []).find(
    (item) =>
      item.kind === 'genesis' &&
      (item.status === 'running' || item.status === 'queued')
  )
  const notes = lines.filter((line) => line.actor === 'system')
  return (
    <section
      aria-label='Genesis in progress'
      data-onboarding='progress'
      className='flex w-full max-w-2xl min-w-0 flex-col items-center gap-6 self-center rounded-xl border bg-card p-6 text-center shadow-sm'
    >
      <div className='relative flex h-40 w-40 items-center justify-center'>
        <span
          aria-hidden='true'
          className='absolute inset-0 animate-ping rounded-full bg-primary/15 motion-reduce:animate-none'
        />
        <span
          aria-hidden='true'
          className='absolute inset-3 rounded-full bg-linear-to-br from-primary/30 via-brand-violet/25 to-brand-magenta/20 blur-md'
        />
        <span className='relative flex h-32 w-32 items-center justify-center'>
          <Logo size='md' className='size-full' />
        </span>
      </div>
      <div className='flex min-w-0 flex-col items-center gap-1'>
        <PageTitle>The world is being thought</PageTitle>
        <Muted variant='prose'>
          The cosmology, the language, your likeness, the first land, the first
          star and your first sons are taking shape. You will be taken to your
          world when it is ready.
        </Muted>
      </div>
      <div className='w-full min-w-0 text-start'>
        {job ? (
          <JobProgress job={job} title='Genesis' />
        ) : (
          <Skeleton className='h-control-lg w-full' />
        )}
      </div>
      {notes.length > 0 && (
        <ol className='flex max-h-80 w-full min-w-0 flex-col gap-1.5 overflow-y-auto rounded-lg border bg-muted/30 p-3 text-start'>
          {notes.map((line, index) => {
            const latest = index === notes.length - 1
            return (
              <li key={line.id} className='flex min-w-0 items-start gap-2'>
                {latest ? (
                  <LoaderCircle
                    aria-hidden='true'
                    className='size-icon-sm shrink-0 animate-spin text-primary motion-reduce:animate-none'
                  />
                ) : (
                  <CircleCheck
                    aria-hidden='true'
                    className='size-icon-sm shrink-0 text-success'
                  />
                )}
                <Text
                  as='span'
                  variant='caption'
                  tone={latest ? 'default' : 'muted'}
                >
                  {line.title}
                </Text>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}

function RestoreWorld() {
  return (
    <Collapsible className='flex min-w-0 flex-col gap-4'>
      <CollapsibleTrigger asChild>
        <Button variant='ghost' className='self-center'>
          <ArchiveRestore />
          Already have a world? Open a world file or a backup
          <ChevronDown />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-6'>
        <ShareWorld hasWorld={false} readOnly={false} />
        <BackupsPanel readOnly={false} />
      </CollapsibleContent>
    </Collapsible>
  )
}

function Hero() {
  return (
    <header className='relative flex w-full max-w-3xl min-w-0 flex-col items-center gap-4 text-center'>
      <div className='relative flex items-center justify-center'>
        <span
          aria-hidden='true'
          className='absolute inset-4 rounded-full bg-linear-to-br from-primary/35 via-brand-violet/30 to-brand-magenta/25 blur-2xl'
        />
        <span className='relative flex h-36 w-36 items-center justify-center sm:h-44 sm:w-44'>
          <Logo
            size='md'
            className='size-full drop-shadow-xl'
            title={APP_NAME}
          />
        </span>
      </div>
      <div className='flex min-w-0 flex-col items-center gap-1'>
        <Text as='span' weight='semibold' className='font-brand text-primary'>
          {`${APP_NAME}®`}
        </Text>
        <Label variant='overline'>{APP_SUBTITLE}</Label>
      </div>
      <PageTitle>You are alone in the void.</PageTitle>
      <Muted variant='prose'>
        Give yourself a name and the world a seed. From this seed it grows its
        cosmology, its language, your likeness, its first land, the first star
        in its sky and your first sons.
      </Muted>
    </header>
  )
}

export function GenesisScreen() {
  const state = useWorldState()
  const jobs = useRecentJobs()
  const navigate = useNavigate()
  const expectGenesis = useRevealQueue((store) => store.expectGenesis)
  useEvent('genesis.finished', () => {
    expectGenesis()
    void navigate({ to: '/' })
  })
  const running = (jobs.data ?? []).some(
    (item) =>
      item.kind === 'genesis' &&
      (item.status === 'running' || item.status === 'queued')
  )
  const world = state.data?.world ?? null
  const llm = state.data?.llm_enabled ?? false
  return (
    <main
      id='content'
      className='relative flex min-h-svh flex-col items-center gap-10 overflow-x-clip bg-background px-4 py-10 sm:py-14'
    >
      <span
        aria-hidden='true'
        className='pointer-events-none absolute inset-x-0 top-0 h-160 bg-linear-to-b from-brand-violet/12 via-primary/5 to-transparent'
      />
      <FeedCollector />
      <Hero />
      <div className='relative flex w-full max-w-6xl min-w-0 flex-col gap-8'>
        {state.isPending && <Skeleton className='h-160 w-full' />}
        {state.isError && <Text tone='destructive'>{state.error.message}</Text>}
        {state.data && running && <GenesisProgress />}
        {state.data && !running && world && (
          <div className='flex w-full max-w-2xl min-w-0 flex-col self-center rounded-xl border bg-card p-6 shadow-sm'>
            <EmptyState
              icon={Globe}
              title={`${world.name} already exists`}
              description='A world can only be created once. Reset it in Settings, Data, to begin again.'
              action={
                <Button variant='outline' asChild>
                  <Link to='/'>
                    <ArrowLeft />
                    Back to the overview
                  </Link>
                </Button>
              }
            />
          </div>
        )}
        {state.data && !running && !world && (
          <>
            {!llm && (
              <Alert variant='destructive'>
                <CircleAlert />
                <AlertTitle>The language model is turned off</AlertTitle>
                <AlertDescription>
                  You can shape the whole world below, but genesis writes it
                  with the language model. Configure the Claude token on the
                  server and restart it to create the world, or open an existing
                  world instead.
                </AlertDescription>
              </Alert>
            )}
            <GenesisWizard llmEnabled={llm} />
            <RestoreWorld />
          </>
        )}
      </div>
    </main>
  )
}
