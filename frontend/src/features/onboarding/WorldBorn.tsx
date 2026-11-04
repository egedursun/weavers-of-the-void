import { useEffect, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import {
  ArrowRight,
  Crown,
  Languages,
  MapPinned,
  Mountain,
  Sparkles,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MiniStat } from '@/components/domain'
import { Logo } from '@/components/layout/Logo'
import { Label, Muted, PageTitle } from '@/components/typography'
import { type WorldState } from '@/features/overview/api'

const ENTER_AFTER_SECONDS = 6
const TICK_MS = 1000

export function WorldBorn({ state }: { state: WorldState }) {
  const navigate = useNavigate()
  const [left, setLeft] = useState(ENTER_AFTER_SECONDS)
  useEffect(() => {
    const timer = window.setInterval(
      () => setLeft((before) => Math.max(0, before - 1)),
      TICK_MS
    )
    return () => window.clearInterval(timer)
  }, [])
  useEffect(() => {
    if (left === 0) void navigate({ to: '/' })
  }, [left, navigate])
  const world = state.world
  const creator = state.creator
  const counts = state.counts as Record<string, number | undefined>
  return (
    <section
      aria-label='The world is born'
      data-onboarding='born'
      className='relative flex w-full max-w-2xl min-w-0 flex-col items-center gap-6 self-center overflow-hidden rounded-xl border border-primary/40 bg-card p-8 text-center shadow-lg'
    >
      <span
        aria-hidden='true'
        className='pointer-events-none absolute inset-x-0 top-0 h-64 bg-linear-to-b from-primary/20 via-brand-violet/10 to-transparent'
      />
      <div className='relative flex h-40 w-40 items-center justify-center'>
        <span
          aria-hidden='true'
          className='absolute inset-2 rounded-full bg-linear-to-br from-primary/45 via-brand-violet/35 to-brand-magenta/30 blur-xl'
        />
        <span className='relative flex h-36 w-36 items-center justify-center'>
          <Logo size='md' className='size-full drop-shadow-xl' />
        </span>
      </div>
      <div className='relative flex min-w-0 flex-col items-center gap-2'>
        <span className='flex items-center gap-1.5 text-primary'>
          <Sparkles aria-hidden='true' className='size-icon-xs' />
          <Label variant='overline' className='text-primary'>
            Genesis complete
          </Label>
        </span>
        <PageTitle>{`${world?.name ?? 'Your world'} is born.`}</PageTitle>
        <Muted variant='prose'>
          {creator
            ? `${creator.name}${creator.title ? `, ${creator.title},` : ''} looks upon the first land, the first peoples and the first star in its sky. Your sons wait for your word.`
            : 'The first land, the first peoples and the first star in its sky wait for your word.'}
        </Muted>
      </div>
      <div className='relative grid w-full min-w-0 grid-cols-2 gap-2 text-start sm:grid-cols-4'>
        <MiniStat
          icon={Crown}
          label='Sons'
          value={state.sons.length}
          tone='gold'
        />
        <MiniStat
          icon={Users}
          label='Peoples'
          value={counts.people ?? 0}
          tone='info'
        />
        <MiniStat
          icon={Mountain}
          label='Lands'
          value={counts.region ?? 0}
          tone='success'
        />
        <MiniStat
          icon={Languages}
          label='Tongues'
          value={counts.language ?? 0}
          tone='verdigris'
        />
      </div>
      <div className='relative flex min-w-0 flex-col items-center gap-2'>
        <Button size='lg' onClick={() => void navigate({ to: '/' })}>
          <MapPinned />
          Enter your world
          <ArrowRight />
        </Button>
        <Muted variant='caption' aria-live='polite'>
          {`Taking you there in ${left}…`}
        </Muted>
      </div>
    </section>
  )
}
