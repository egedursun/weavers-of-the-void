import { useState } from 'react'
import {
  AlarmClock,
  Droplet,
  Flame,
  Mountain,
  Skull,
  Swords,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { FormRow, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { NamePicker } from '@/features/pantheon/NamePicker'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { type ForeignGodDetail } from './api'

const REASON_MAX = 300

export function ForeignGodPowerPanel({ detail }: { detail: ForeignGodDetail }) {
  const god = detail.god
  const godId = god.id
  const path = { params: { path: { god_id: godId } } }
  const { reason } = useGodGate()
  const [why, setWhy] = useState('')
  const [devour, setDevour] = useState(false)
  const [target, setTarget] = useState<string | null>(null)
  const [temple, setTemple] = useState<string | null>(null)
  const deathless = detail.powers.some((power) => power.effect === 'deathless')
  const drained = detail.drain_amount
  const drainGain = detail.drain_gain
  const killCost = detail.kill_cost
  const drain = useGodAction({
    run: () => unwrap(api.POST('/api/foreign-gods/{god_id}/drain', path)),
    success: 'Power drained',
  })
  const kill = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/foreign-gods/{god_id}/kill', {
          ...path,
          body: { reason: why.trim(), devour },
        })
      ),
    success: `${god.name} died`,
  })
  const wake = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/foreign_god:wake', { body: { god_id: godId } })
      ),
  })
  const raise = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/foreign_god:raise_land', {
          body: { god_id: godId },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/foreign_god:strike', {
          body: { god_id: godId, entity_id: Number(target) },
        })
      ),
  })
  const raid = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/foreign_god:raid_temple', {
          body: { god_id: godId, temple_id: Number(temple) },
        })
      ),
  })
  if (god.status === 'dead')
    return (
      <Section
        title={
          god.death_epoch !== null
            ? `${god.name} died · Epoch ${god.death_epoch}`
            : `${god.name} is dead`
        }
        surface='card'
        level={3}
      >
        <Muted>
          To revive this god, change the status in the edit form below.
        </Muted>
      </Section>
    )
  const worldId = detail.world?.id ?? null
  return (
    <Section
      title="God's power"
      description='Foreign gods wake, strike, raise land and raid temples on their own; here you can force each of these.'
      surface='card'
      level={3}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <ActionButton
          label='Drain power'
          icon={Droplet}
          variant='destructive'
          gain={drainGain}
          blocked={
            reason() ?? (drained === 0 ? 'No power left to drain.' : null)
          }
          pending={drain.isPending}
          confirm={{
            title: 'Drain this power?',
            description:
              'The attitude toward the pantheon drops; when the power runs out the god is defeated.',
          }}
          onRun={() => drain.mutate()}
        />
        {(god.status === 'asleep' || god.status === 'defeated') && (
          <ActionButton
            label='Wake'
            icon={AlarmClock}
            blocked={reason()}
            pending={wake.isPending}
            confirm={{
              title: `Wake ${god.name}?`,
              description: 'The god rises with a grudge against the pantheon.',
            }}
            onRun={() => wake.mutate()}
          />
        )}
        <ActionButton
          label='Raise new land'
          icon={Mountain}
          blocked={reason()}
          pending={raise.isPending}
          onRun={() => raise.mutate()}
        />
      </div>
      <Separator />
      <div className='flex min-w-0 flex-col gap-3'>
        <FieldLabel htmlFor={`fg-reason-${godId}`}>
          Why? Written in the chronicle
        </FieldLabel>
        <Input
          id={`fg-reason-${godId}`}
          value={why}
          maxLength={REASON_MAX}
          onChange={(event) => setWhy(event.target.value)}
        />
        <div className='flex min-w-0 items-center gap-2'>
          <Checkbox
            id={`fg-devour-${godId}`}
            checked={devour}
            onCheckedChange={(value) => setDevour(value === true)}
          />
          <FieldLabel htmlFor={`fg-devour-${godId}`}>
            Devour: the power passes to you
          </FieldLabel>
        </div>
        <div>
          <ActionButton
            label='Kill'
            icon={Skull}
            variant='destructive'
            cost={killCost}
            blocked={reason({ cost: killCost, world: true })}
            pending={kill.isPending}
            confirm={{
              title: `Kill ${god.name}?`,
              description:
                'Some worshippers may turn to you; the others become godless.',
            }}
            onRun={() => kill.mutate()}
          />
        </div>
        {deathless && (
          <Text variant='caption'>Deathless: killing costs more.</Text>
        )}
      </div>
      <Separator />
      <FormRow
        label='Strike a mortal'
        description='A mortal of this world who does not worship the god.'
      >
        {(id) => (
          <>
            <NamePicker
              id={id}
              value={target}
              kinds={['entity']}
              types={['mortal']}
              worldId={worldId}
              onChange={(value) => setTarget(value)}
            />
            <ActionButton
              label='Strike'
              icon={Flame}
              variant='destructive'
              blocked={reason() ?? (target ? null : 'Pick a mortal.')}
              pending={strike.isPending}
              onRun={() => strike.mutate()}
            />
          </>
        )}
      </FormRow>
      <FormRow
        label='Raid a temple'
        description='A temple of the pantheon on this world.'
      >
        {(id) => (
          <>
            <NamePicker
              id={id}
              value={temple}
              kinds={['entity']}
              types={['structure']}
              worldId={worldId}
              onChange={(value) => setTemple(value)}
            />
            <ActionButton
              label='Raid'
              icon={Swords}
              variant='destructive'
              blocked={reason() ?? (temple ? null : 'Pick a temple.')}
              pending={raid.isPending}
              onRun={() => raid.mutate()}
            />
          </>
        )}
      </FormRow>
    </Section>
  )
}
