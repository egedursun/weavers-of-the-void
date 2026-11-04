import { useState } from 'react'
import { Castle, Flag, MapPin, ScrollText, Swords, Users } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { RecordPanel } from './RecordPanel'
import { CAUSE } from './depth'
import { AIM, FAMILY, TACTIC, busyOf } from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  NumberField,
  Panel,
  ToggleField,
} from './parts'

type Cause = components['schemas']['WarCause']
type Aim = components['schemas']['WarAimKind']
const ROLE = {
  commander: { label: 'Commander', icon: Flag, tone: 'gold' as const },
  sub_commander: { label: 'Sub-commander', icon: Users, tone: 'info' as const },
  quartermaster: {
    label: 'Quartermaster',
    icon: ScrollText,
    tone: 'success' as const,
  },
  standard_bearer: {
    label: 'Standard bearer',
    icon: Flag,
    tone: 'warning' as const,
  },
  surgeon: { label: 'Surgeon', icon: Users, tone: 'verdigris' as const },
}

function IdField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <label className='flex min-w-0 flex-col gap-1'>
      <Text as='span' variant='caption'>
        {label}
      </Text>
      <Input
        type='number'
        inputMode='numeric'
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  )
}

export function ArmyOrders({
  armyId,
  blocked,
}: {
  armyId: number
  blocked: string | null
}) {
  const [commander, setCommander] = useState('')
  const [owner, setOwner] = useState('')
  const assign = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/army:assign', {
          body: {
            army_id: armyId,
            commander_id: commander ? Number(commander) : null,
            owner_id: owner ? Number(owner) : null,
          },
        })
      ),
  })
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Adjust
        title='Leadership'
        note='Set who commands the army and whom it serves.'
        label='Leadership'
      >
        <FieldGrid>
          <IdField
            label='Commander (mortal id)'
            value={commander}
            onChange={setCommander}
          />
          <IdField
            label='Serves (community id)'
            value={owner}
            onChange={setOwner}
          />
        </FieldGrid>
        <Button
          size='sm'
          className='self-start'
          disabled={busyOf(blocked, assign.isPending) !== null}

          disabledReason={
            busyOf(blocked, assign.isPending) !== null
              ? (blocked ?? 'Fill in what is needed first')
              : undefined
          }
          onClick={() => assign.mutate()}
        >
          <Flag />
          Assign
        </Button>
      </Adjust>
      <RecordPanel
        kind='army_profile'
        scope={armyId}
        title='Orders and tactic'
        blocked={blocked}
        choices={{ tactic: TACTIC }}
        hint='Preferred tactic, stance, drill, fodder, mutiny and more'
      />
      <RecordPanel
        kind='officer'
        scope={armyId}
        title='Officers'
        blocked={blocked}
        presets={{ army_entity_id: armyId }}
        choices={{ role: ROLE }}
        hint='Commander and sub-commanders as offices of the army'
      />
      <RecordPanel
        kind='stack'
        scope={armyId}
        title='Stacks: every value'
        blocked={blocked}
        presets={{ army_entity_id: armyId }}
        hint='Weapons, material, class, origin, condition and holds'
      />
    </div>
  )
}

export function WarOrders({
  warId,
  sides,
  blocked,
}: {
  warId: number
  sides: { id: number; name: string }[]
  blocked: string | null
}) {
  const [region, setRegion] = useState('')
  const [army, setArmy] = useState('')
  const [settlement, setSettlement] = useState('')
  const battle = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:battle_at', {
          body: { war_id: warId, region_id: region ? Number(region) : null },
        })
      ),
  })
  const siege = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/siege:start', {
          body: {
            war_id: warId,
            army_id: Number(army),
            settlement_id: Number(settlement),
          },
        })
      ),
  })
  return (
    <Panel
      title='Orders of war'
      icon={Swords}
      tone='danger'
      hint={sides.map((side) => side.name).join(' against ')}
    >
      <Adjust
        title='Force a battle'
        note='Fight now, where the armies meet or in a region of your choosing.'
        label='Force a battle'
      >
        <FieldGrid>
          <IdField
            label='Region id (optional)'
            value={region}
            onChange={setRegion}
          />
        </FieldGrid>
        <Button
          size='sm'
          className='self-start'
          disabled={busyOf(blocked, battle.isPending) !== null}

          disabledReason={
            busyOf(blocked, battle.isPending) !== null
              ? (blocked ?? 'Fill in what is needed first')
              : undefined
          }
          onClick={() => battle.mutate()}
        >
          <MapPin />
          Fight here
        </Button>
      </Adjust>
      <Adjust
        title='Lay siege'
        note='Set an army of one side against a settlement of the other.'
        label='Lay siege'
      >
        <FieldGrid>
          <IdField label='Army id' value={army} onChange={setArmy} />
          <IdField
            label='Settlement id'
            value={settlement}
            onChange={setSettlement}
          />
        </FieldGrid>
        <Button
          size='sm'
          className='self-start'
          disabled={
            busyOf(blocked, siege.isPending) !== null || !army || !settlement
          }

          disabledReason={
            busyOf(blocked, siege.isPending) !== null || !army || !settlement
              ? (blocked ?? 'Fill in what is needed first')
              : undefined
          }
          onClick={() => siege.mutate()}
        >
          <Castle />
          Begin the siege
        </Button>
      </Adjust>
      <RecordPanel
        kind='war'
        scope={null}
        title='War record'
        blocked={blocked}
        choices={{ cause: CAUSE }}
        hidden={['incited_by_son_id']}
      />
      <RecordPanel
        kind='siege'
        scope={warId}
        title='Sieges: every value'
        blocked={blocked}
        presets={{ war_id: warId }}
      />
      <RecordPanel
        kind='war_aim'
        scope={warId}
        title='Aims and their parameters'
        blocked={blocked}
        presets={{ war_id: warId }}
        choices={{ kind: AIM }}
      />
    </Panel>
  )
}

export function RaiseArmy({
  communityId,
  blocked,
}: {
  communityId: number
  blocked: string | null
}) {
  const [size, setSize] = useState('500')
  const [commander, setCommander] = useState('')
  const [name, setName] = useState('')
  const raise = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/army:raise', {
          body: {
            community_id: communityId,
            size: Number(size) || 1,
            commander_id: commander ? Number(commander) : null,
            name: name || null,
          },
        })
      ),
  })
  return (
    <Adjust
      title='Raise an army'
      note='Levy soldiers from this community, in war or in peace.'
      label='Raise an army'
    >
      <FieldGrid>
        <NumberField
          label='Soldiers'
          icon={Users}
          value={size}
          onChange={setSize}
          min={1}
        />
        <IdField
          label='Commander (mortal id)'
          value={commander}
          onChange={setCommander}
        />
        <label className='flex min-w-0 flex-col gap-1'>
          <Text as='span' variant='caption'>
            Name
          </Text>
          <Input
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
      </FieldGrid>
      <Button
        size='sm'
        className='self-start'
        disabled={busyOf(blocked, raise.isPending) !== null}

        disabledReason={
          busyOf(blocked, raise.isPending) !== null
            ? (blocked ?? 'Fill in what is needed first')
            : undefined
        }
        onClick={() => raise.mutate()}
      >
        <Users />
        Raise
      </Button>
    </Adjust>
  )
}

export function DeclareWar({
  attackerId,
  blocked,
}: {
  attackerId: number
  blocked: string | null
}) {
  const [defender, setDefender] = useState('')
  const [cause, setCause] = useState('claim')
  const [aims, setAims] = useState<Record<string, boolean>>({})
  const declare = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:declare', {
          body: {
            attacker_id: attackerId,
            defender_id: Number(defender),
            cause: cause as Cause,
            reason: '',
            aims: Object.entries(aims)
              .filter(([, on]) => on)
              .map(([kind]) => ({ kind: kind as Aim, params: {} })),
          },
        })
      ),
  })
  return (
    <Adjust
      title='Declare a war'
      note='Name the cause and the aims; aims fill in their own parameters.'
      label='Declare a war'
    >
      <FieldGrid>
        <IdField
          label='Against (community id)'
          value={defender}
          onChange={setDefender}
        />
        <ChoiceField
          label='Cause'
          value={cause}
          table={CAUSE}
          blocked={blocked}
          onPick={setCause}
        />
      </FieldGrid>
      <FieldGrid>
        {Object.entries(AIM).map(([kind, item]) => (
          <ToggleField
            key={kind}
            item={item}
            checked={Boolean(aims[kind])}
            disabled={blocked !== null}
            onChange={(next) =>
              setAims((current) => ({ ...current, [kind]: next }))
            }
          />
        ))}
      </FieldGrid>
      <Button
        size='sm'
        className='self-start'
        disabled={busyOf(blocked, declare.isPending) !== null || !defender}

        disabledReason={
          busyOf(blocked, declare.isPending) !== null || !defender
            ? (blocked ?? 'Fill in what is needed first')
            : undefined
        }
        onClick={() => declare.mutate()}
      >
        <Swords />
        Declare
      </Button>
    </Adjust>
  )
}

export function UnitDesigns({ blocked }: { blocked: string | null }) {
  return (
    <RecordPanel
      kind='unit_design'
      scope={null}
      title='Unit designs'
      blocked={blocked}
      choices={{ family: FAMILY }}
      hint='Forge a new kind of soldier on a base unit and family; every value is yours'
    />
  )
}
