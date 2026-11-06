import { useState } from 'react'
import { Lock, Unlock } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { EmptyState, KpiTile, Section } from '@/components/domain'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { type Bonds, useBonds } from '../bonds/api'
import {
  BondsCard,
  CirclesCard,
  ContestsCard,
  PassionsCard,
  PersuasionsCard,
  StandingCard,
} from '../bonds/cards'
import {
  BONDS_ICON,
  CIRCLE_ICON,
  CONTEST_ICON,
  PASSION_ICON,
  STANDING_ICON,
} from '../bonds/labels'
import { ControlPanel } from '../mind/parts'

const WORKING = 'Working on it.'
const FRIENDLY = new Set(['friend', 'close_friend', 'best_friend', 'confidant'])
const LOVING = new Set(['crush', 'lover', 'spouse'])
const HOSTILE = new Set(['rival', 'nemesis', 'enemy'])

function count(view: Bonds, kinds: Set<string>) {
  return view.bonds.filter((bond) => bond.kinds.some((kind) => kinds.has(kind)))
    .length
}

function HoldControls({
  view,
  hold,
  onHold,
}: {
  view: Bonds
  hold: boolean
  onHold: (value: boolean) => void
}) {
  const { reason } = useGodGate()
  const lock = useGodAction({
    run: (input: { field: string; locked: boolean }) =>
      unwrap(
        api.POST(
          input.locked ? '/api/actions/mind:unlock' : '/api/actions/mind:lock',
          { body: { node_id: view.node_id, field: input.field } }
        )
      ),
  })
  const busy = reason() ?? (lock.isPending ? WORKING : null)
  return (
    <ControlPanel
      title='Hold hearts and passions'
      note='Hold a mortal’s bonds or passions so the world stops changing them. Values you set below are held while the switch is on. Every change goes into the ledger and can be undone.'
      hold={hold}
      onHold={onHold}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          variant={view.bonds_held ? 'outline' : 'ghost'}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() =>
            lock.mutate({ field: 'relations', locked: view.bonds_held })
          }
        >
          {view.bonds_held ? <Unlock /> : <Lock />}
          {view.bonds_held ? 'Release bonds' : 'Hold bonds'}
        </Button>
        <Button
          size='sm'
          variant={view.passions_held ? 'outline' : 'ghost'}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() =>
            lock.mutate({ field: 'passions', locked: view.passions_held })
          }
        >
          {view.passions_held ? <Unlock /> : <Lock />}
          {view.passions_held ? 'Release passions' : 'Hold passions'}
        </Button>
      </div>
    </ControlPanel>
  )
}

function MortalBonds({
  view,
  blocked,
}: {
  view: Bonds
  blocked: string | null
}) {
  const [hold, setHold] = useState(true)
  const best =
    view.ranks.length > 0
      ? Math.min(...view.ranks.map((rank) => rank.rank))
      : null
  const strongest = view.passions[0]?.strength ?? 0
  return (
    <div className='@container/mind flex min-w-0 flex-col gap-4'>
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/mind:grid-cols-2 @3xl/mind:grid-cols-5'>
        <KpiTile
          label='Friends'
          value={count(view, FRIENDLY)}
          icon={BONDS_ICON}
          tone='success'
        />
        <KpiTile
          label='Loves'
          value={count(view, LOVING)}
          icon={BONDS_ICON}
          tone='danger'
        />
        <KpiTile
          label='Rivals and foes'
          value={count(view, HOSTILE)}
          icon={CONTEST_ICON}
          tone='warning'
        />
        <KpiTile
          label='Strongest passion'
          value={strongest}
          icon={PASSION_ICON}
          tone='gold'
          meter={{ value: strongest, max: 100, label: 'Passion' }}
        />
        <KpiTile
          label='Best standing'
          value={best === null ? 'None' : `Rank ${best}`}
          icon={STANDING_ICON}
          tone='verdigris'
        />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 @xl/mind:grid-cols-2'>
        <BondsCard view={view} blocked={blocked} hold={hold} />
        <PassionsCard view={view} blocked={blocked} hold={hold} />
        <StandingCard view={view} blocked={blocked} hold={hold} />
        <CirclesCard view={view} blocked={blocked} hold={hold} place={false} />
        <ContestsCard view={view} blocked={blocked} hold={hold} mortal />
        <PersuasionsCard view={view} blocked={blocked} hold={hold} />
      </div>
      <HoldControls view={view} hold={hold} onHold={setHold} />
    </div>
  )
}

function GroupBonds({
  view,
  blocked,
}: {
  view: Bonds
  blocked: string | null
}) {
  const [hold] = useState(true)
  return (
    <div className='@container/mind flex min-w-0 flex-col gap-4'>
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/mind:grid-cols-3'>
        <KpiTile
          label='Ranked members'
          value={view.order.length}
          icon={STANDING_ICON}
          tone='gold'
        />
        <KpiTile
          label='Circles'
          value={view.circles.length}
          icon={CIRCLE_ICON}
          tone='success'
        />
        <KpiTile
          label='Contests'
          value={view.contests.length}
          icon={CONTEST_ICON}
          tone='warning'
        />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 @xl/mind:grid-cols-2'>
        {view.order.length > 0 && (
          <StandingCard view={view} blocked={blocked} hold={hold} />
        )}
        <CirclesCard
          view={view}
          blocked={blocked}
          hold={hold}
          place={view.place}
        />
        {view.contests.length > 0 && (
          <ContestsCard
            view={view}
            blocked={blocked}
            hold={hold}
            mortal={false}
          />
        )}
      </div>
    </div>
  )
}

export function BondsSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const query = useBonds(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section
        id='section-bonds'
        title='Bonds, passions and standing'
        icon={BONDS_ICON}
      >
        <EmptyState
          icon={BONDS_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view || !view.applies) return null
  return (
    <Section
      id='section-bonds'
      title='Bonds, passions and standing'
      description='Friendships, loves and rivalries; passions that lift or break; circles, pecking orders, contests of wit and arguments.'
      icon={BONDS_ICON}
    >
      {view.mortal ? (
        <MortalBonds view={view} blocked={reason()} />
      ) : (
        <GroupBonds view={view} blocked={reason()} />
      )}
    </Section>
  )
}
