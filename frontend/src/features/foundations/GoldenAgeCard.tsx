import { useState } from 'react'
import {
  CalendarClock,
  Feather,
  Hourglass,
  Lock,
  Save,
  Sun,
  SunDim,
  TrendingUp,
  TriangleAlert,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { EmptyState, KpiTile, Section, LoadingBlock } from '@/components/domain'
import { Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { Adjust } from '@/features/wars/military/parts'
import { type GoldenAge, useGoldenAge } from './api'
import { HoldToggle } from './parts'

function softness(age: GoldenAge): string {
  if (!age.active) return 'No age of ease to wear it down'
  if (age.decadence > 0)
    return `Warriors and walls lose ${age.decadence} each age`
  if (age.decadence_epochs === 0) return 'This world never grows soft'
  return `Turns soft after ${age.decadence_epochs} ages`
}

function GoldenAgeControls({
  worldId,
  age,
  blocked,
}: {
  worldId: number
  age: GoldenAge
  blocked: string | null
}) {
  const [since, setSince] = useState(String(age.since_epoch ?? ''))
  const [hold, setHold] = useState(true)
  const target = { body: { world_id: worldId } }
  const proclaim = useGodAction({
    run: () => unwrap(api.POST('/api/actions/world:golden_age', target)),
  })
  const end = useGodAction({
    run: () => unwrap(api.POST('/api/actions/world:end_golden_age', target)),
  })
  const date = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/world:date_golden_age', {
          body: { world_id: worldId, since_epoch: Number(since), hold },
        })
      ),
  })
  const pending = proclaim.isPending || end.isPending || date.isPending
  const busy = blocked ?? (pending ? 'Working…' : null)
  return (
    <Adjust
      label='Shape the age'
      title='Golden age'
      note='Begin or end it, set the age it began from, and hold it so the world neither starts nor ends one on its own. Every change can be undone.'
    >
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => proclaim.mutate(undefined)}
        >
          <Sun />
          {age.active ? 'Renew the golden age' : 'Proclaim a golden age'}
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || !age.active}
          disabledReason={busy ?? (age.active ? undefined : 'No golden age')}
          onClick={() => end.mutate(undefined)}
        >
          <SunDim />
          End the golden age
        </Button>
      </div>
      <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-3'>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <FieldLabel htmlFor={`golden-since-${worldId}`}>
            Began in age
          </FieldLabel>
          <Input
            id={`golden-since-${worldId}`}
            type='number'
            inputMode='numeric'
            min={0}
            value={since}
            disabled={!age.active}
            onChange={(event) => setSince(event.target.value)}
          />
        </div>
        <label className='flex min-w-0 items-center gap-2 rounded-lg border bg-background p-2.5'>
          <Switch
            checked={hold}
            onCheckedChange={setHold}
            aria-label='Hold the golden age'
          />
          <Text as='span'>Hold it</Text>
        </label>
        <Button
          size='sm'
          disabled={busy !== null || !age.active || since === ''}
          disabledReason={busy ?? (age.active ? undefined : 'No golden age')}
          onClick={() => date.mutate(undefined)}
        >
          <Save />
          Set the date
        </Button>
      </div>
      <HoldToggle
        kind='golden_age'
        nodeId={worldId}
        held={age.held}
        blocked={blocked}
        what='the golden age'
      />
    </Adjust>
  )
}

export function GoldenAgeSection({ worldId }: { worldId: number }) {
  const view = useGoldenAge(worldId)
  const { reason } = useGodGate()
  const blocked = reason()
  return (
    <Section
      id='section-golden-age'
      title='Golden age'
      description='Peace and plenty that deepen with every age, until ease makes the peoples soft.'
      icon={Sun}
    >
      {view.isPending && <LoadingBlock label='Reading the age' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The age could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div data-surface='GoldenAge' className='flex min-w-0 flex-col gap-4'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Badge size='sm' variant={view.data.active ? 'default' : 'outline'}>
              {view.data.active ? <Sun /> : <SunDim />}
              {view.data.active ? 'A golden age' : 'An ordinary age'}
            </Badge>
            {view.data.held && (
              <Badge size='sm' variant='outline'>
                <Lock aria-hidden='true' />
                Held
              </Badge>
            )}
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4'>
            <KpiTile
              label='Since'
              value={
                view.data.since_epoch === null
                  ? '—'
                  : `Age ${view.data.since_epoch}`
              }
              icon={CalendarClock}
              tone={view.data.active ? 'gold' : 'muted'}
              hint={
                view.data.active
                  ? `${view.data.epochs} ages of plenty`
                  : 'Not begun'
              }
            />
            <KpiTile
              label='Prosperity each age'
              value={view.data.active ? `+${view.data.prosperity_gain}` : '—'}
              icon={TrendingUp}
              tone='success'
              hint={`Deepens every ${view.data.deepening_epochs} ages, ${view.data.deepening_steps} times at most`}
            />
            <KpiTile
              label='Softness'
              value={
                view.data.decadence > 0 ? `−${view.data.decadence}` : 'None'
              }
              icon={view.data.decadence > 0 ? Feather : Hourglass}
              tone={view.data.decadence > 0 ? 'warning' : 'muted'}
              hint={softness(view.data)}
            />
            <KpiTile
              label='Sharing it'
              value={`${view.data.golden_communities} / ${view.data.communities}`}
              icon={Users}
              tone='info'
              hint='Peoples and settlements sharing the age'
            />
          </div>
          <GoldenAgeControls
            worldId={worldId}
            age={view.data}
            blocked={blocked}
          />
        </div>
      )}
    </Section>
  )
}
