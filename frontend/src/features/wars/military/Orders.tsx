import { useState } from 'react'
import {
  Castle,
  Crown,
  Flag,
  Flame,
  MapPin,
  Scale,
  ScrollText,
  Swords,
  Target,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { MiniStat, StatBar, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { EntityPicker, Held, RecordButtons, TextField } from './controls'
import {
  CAUSE,
  SACK_CHOICE,
  SIEGE_WORK,
  WALL_MATERIAL,
  nameOf,
  useRecords,
} from './depth'
import { AIM, busyOf } from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  NumberField,
  Panel,
  Tag,
  ToggleField,
} from './parts'
import { type Values, useRecordActions } from './recordHooks'

type Cause = components['schemas']['WarCause']
type Aim = components['schemas']['WarAimKind']
const COMMUNITIES = ['people', 'settlement', 'faction', 'cult', 'polity']
const PERCENT = 100

function ActionButton({
  label,
  icon: Icon,
  busy,
  missing,
  onClick,
}: {
  label: string
  icon: typeof Flag
  busy: string | null
  missing?: string
  onClick: () => void
}) {
  const reason = busy ?? missing
  return (
    <Button
      size='sm'
      className='self-start'
      disabled={reason !== undefined && reason !== null}
      disabledReason={reason ?? undefined}
      onClick={onClick}
    >
      <Icon />
      {label}
    </Button>
  )
}

export function WarLedger({
  warId,
  blocked,
}: {
  warId: number
  blocked: string | null
}) {
  const rows = useRecords('war', warId)
  const row = rows.data?.rows[0]
  const actions = useRecordActions('war', warId, warId)
  const [draft, setDraft] = useState<Values>({})
  if (!row) return null
  const value = (key: string) => (key in draft ? draft[key] : row.values[key])
  return (
    <Panel
      title='The war itself'
      icon={Scale}
      tone='danger'
      hint='Its cause, its score and how bloody it has become'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Tag item={nameOf(CAUSE, String(row.values.cause))} />
        <Held locked={row.locked} />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <MiniStat
          icon={Scale}
          label='Score'
          value={Number(row.values.score ?? 0)}
          tone='gold'
          hint='Above zero favours the attackers'
        />
        <MiniStat
          icon={Flame}
          label='Violence'
          value={Number(row.values.violence ?? 0)}
          tone='danger'
        />
      </div>
      <Adjust
        title='Set the war'
        note='Change its cause, score or violence; held values stay until released.'
      >
        <FieldGrid>
          <ChoiceField
            label='Cause'
            value={String(value('cause'))}
            table={CAUSE}
            blocked={blocked}
            onPick={(next) => setDraft({ ...draft, cause: next })}
          />
          <NumberField
            label='Score'
            icon={Scale}
            value={String(value('score') ?? 0)}
            min={-100}
            max={100}
            onChange={(next) => setDraft({ ...draft, score: Number(next) })}
          />
          <NumberField
            label='Violence'
            icon={Flame}
            value={String(value('violence') ?? 0)}
            max={100}
            onChange={(next) => setDraft({ ...draft, violence: Number(next) })}
          />
        </FieldGrid>
        <RecordButtons
          actions={actions}
          values={draft}
          locked={row.locked}
          blocked={blocked}
          deletable={false}
        />
      </Adjust>
    </Panel>
  )
}

function SiegeDepthCard({
  siege,
  warId,
  blocked,
}: {
  siege: NonNullable<ReturnType<typeof useRecords>['data']>['rows'][number]
  warId: number
  blocked: string | null
}) {
  const actions = useRecordActions('siege', siege.id, warId)
  const [draft, setDraft] = useState<Values>({})
  const works = (siege.values.works ?? {}) as Record<string, number>
  const city = siege.refs.besieged_entity_id?.name ?? 'The city'
  const relief = siege.refs.relief_army_id?.name
  const choice = siege.values.choice ? String(siege.values.choice) : null
  const material = siege.values.wall_material
    ? String(siege.values.wall_material)
    : null
  return (
    <div className='flex min-w-0 flex-col gap-2.5 rounded-lg border bg-background p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Text as='span' weight='medium' truncate>
          {city}
        </Text>
        {material && <Tag item={nameOf(WALL_MATERIAL, material)} />}
        {choice && <Tag item={nameOf(SACK_CHOICE, choice)} />}
        {relief && (
          <Tag
            item={{ label: `Relief: ${relief}`, icon: Flag, tone: 'success' }}
          />
        )}
        <Held locked={siege.locked} />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-1.5 @lg/mil:grid-cols-2'>
        {Object.entries(SIEGE_WORK).map(([key, item]) => (
          <StatBar
            key={key}
            label={item.label}
            icon={item.icon}
            value={Math.min(PERCENT, Number(works[key] ?? 0))}
            max={PERCENT}
            tone={Number(works[key] ?? 0) >= PERCENT ? 'success' : 'warning'}
          />
        ))}
      </div>
      <Adjust
        title='Siege works and fate'
        note='Choose the walls, the works and what the victors do when the gates fall.'
      >
        <FieldGrid>
          <ChoiceField
            label='Walls'
            value={String(draft.wall_material ?? material ?? 'timber')}
            table={WALL_MATERIAL}
            blocked={blocked}
            onPick={(next) => setDraft({ ...draft, wall_material: next })}
          />
          <ChoiceField
            label='When the gates fall'
            value={String(draft.choice ?? choice ?? 'sack')}
            table={SACK_CHOICE}
            blocked={blocked}
            onPick={(next) => setDraft({ ...draft, choice: next })}
          />
          {Object.entries(SIEGE_WORK).map(([key, item]) => (
            <NumberField
              key={key}
              label={item.label}
              icon={item.icon}
              max={PERCENT}
              value={String(
                ((draft.works as Record<string, number> | undefined) ?? works)[
                  key
                ] ?? 0
              )}
              onChange={(next) =>
                setDraft({
                  ...draft,
                  works: {
                    ...works,
                    ...((draft.works as Record<string, number> | undefined) ??
                      {}),
                    [key]: Number(next),
                  },
                })
              }
            />
          ))}
        </FieldGrid>
        <RecordButtons
          actions={actions}
          values={draft}
          locked={siege.locked}
          blocked={blocked}
          removeLabel='Lift the siege record'
        />
      </Adjust>
    </div>
  )
}

export function SiegeDepth({
  warId,
  blocked,
}: {
  warId: number
  blocked: string | null
}) {
  const sieges = useRecords('siege', warId)
  const rows = sieges.data?.rows ?? []
  if (rows.length === 0) return null
  return (
    <Panel
      title='Siege works'
      icon={Castle}
      tone='warning'
      count={rows.length}
      hint='Walls, works, relief and the fate of the city'
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <Paged items={rows}>
          {(siege) => (
            <SiegeDepthCard
              key={siege.id}
              siege={siege}
              warId={warId}
              blocked={blocked}
            />
          )}
        </Paged>
      </div>
    </Panel>
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
  const [region, setRegion] = useState<number | null>(null)
  const [army, setArmy] = useState<number | null>(null)
  const [settlement, setSettlement] = useState<number | null>(null)
  const battle = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:battle_at', {
          body: { war_id: warId, region_id: region },
        })
      ),
    invalidate: [['wars']],
  })
  const siege = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/siege:start', {
          body: {
            war_id: warId,
            army_id: army ?? 0,
            settlement_id: settlement ?? 0,
          },
        })
      ),
    invalidate: [['wars']],
  })
  return (
    <Panel
      title='Orders of war'
      icon={Swords}
      tone='danger'
      hint={sides.map((side) => side.name).join(' against ')}
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <Adjust
          title='Force a battle'
          note='Fight now, where the armies meet, or in a land you choose.'
          label='Force a battle'
        >
          <FieldGrid>
            <EntityPicker
              label='Battlefield'
              icon={MapPin}
              types={['region']}
              value={region}
              onChange={setRegion}
              blocked={blocked}
            />
          </FieldGrid>
          <ActionButton
            label={region ? 'Fight there' : 'Fight where they meet'}
            icon={MapPin}
            busy={busyOf(blocked, battle.isPending)}
            onClick={() => battle.mutate()}
          />
        </Adjust>
        <Adjust
          title='Lay siege'
          note='Set an army of one side against a settlement of the other.'
          label='Lay siege'
        >
          <FieldGrid>
            <EntityPicker
              label='Besieging army'
              icon={Users}
              types={['army']}
              value={army}
              onChange={setArmy}
              blocked={blocked}
            />
            <EntityPicker
              label='Settlement'
              icon={Castle}
              types={['settlement']}
              value={settlement}
              onChange={setSettlement}
              blocked={blocked}
            />
          </FieldGrid>
          <ActionButton
            label='Begin the siege'
            icon={Castle}
            busy={busyOf(blocked, siege.isPending)}
            missing={
              army && settlement
                ? undefined
                : 'Choose the army and the settlement'
            }
            onClick={() => siege.mutate()}
          />
        </Adjust>
      </div>
    </Panel>
  )
}

export function AimParams({
  aimId,
  kind,
  params,
  locked,
  warId,
  blocked,
}: {
  aimId: number
  kind: string
  params: Record<string, unknown>
  locked: string[]
  warId: number
  blocked: string | null
}) {
  const actions = useRecordActions('war_aim', aimId, warId)
  const [amount, setAmount] = useState(String(params.amount ?? ''))
  const [epochs, setEpochs] = useState(String(params.epochs ?? ''))
  const [target, setTarget] = useState<number | null>(
    typeof params.target === 'number' ? params.target : null
  )
  const money = kind === 'tribute' || kind === 'loot'
  const values: Values = {
    params: {
      ...params,
      ...(money
        ? { amount: Number(amount) || 0, epochs: Number(epochs) || 0 }
        : {}),
      ...(target !== null ? { target } : {}),
    },
  }
  return (
    <Adjust
      title='What winning means'
      note='Set the terms this aim will demand at the peace.'
      label='Terms'
    >
      <FieldGrid>
        {money && (
          <NumberField
            label='Wealth demanded'
            icon={Crown}
            value={amount}
            onChange={setAmount}
          />
        )}
        {kind === 'tribute' && (
          <NumberField
            label='For epochs'
            icon={ScrollText}
            value={epochs}
            onChange={setEpochs}
          />
        )}
        {!money && (
          <EntityPicker
            label='Prize'
            icon={Target}
            types={['region', 'settlement', 'place', 'resource']}
            value={target}
            onChange={setTarget}
            blocked={blocked}
          />
        )}
      </FieldGrid>
      <RecordButtons
        actions={actions}
        values={values}
        locked={locked}
        blocked={blocked}
        removeLabel='Abandon the aim'
      />
    </Adjust>
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
  const [commander, setCommander] = useState<number | null>(null)
  const [name, setName] = useState('')
  const raise = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/army:raise', {
          body: {
            community_id: communityId,
            size: Number(size) || 1,
            commander_id: commander,
            name: name.trim() || null,
          },
        })
      ),
    invalidate: [['entities']],
  })
  return (
    <Adjust
      title='Raise an army'
      note='Levy soldiers from this community, in war or in peace; warriors and nobles answer first.'
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
        <EntityPicker
          label='Commander'
          icon={Crown}
          types={['mortal']}
          value={commander}
          onChange={setCommander}
          blocked={blocked}
        />
        <TextField
          label='Name (optional)'
          icon={Flag}
          value={name}
          onChange={setName}
          placeholder='Named for its people if left empty'
        />
      </FieldGrid>
      <ActionButton
        label='Raise'
        icon={Users}
        busy={busyOf(blocked, raise.isPending)}
        onClick={() => raise.mutate()}
      />
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
  const [defender, setDefender] = useState<number | null>(null)
  const [cause, setCause] = useState('claim')
  const [aims, setAims] = useState<Record<string, boolean>>({})
  const [reason, setReason] = useState('')
  const declare = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:declare', {
          body: {
            attacker_id: attackerId,
            defender_id: defender ?? 0,
            cause: cause as Cause,
            reason: reason.trim(),
            aims: Object.entries(aims)
              .filter(([, on]) => on)
              .map(([kind]) => ({ kind: kind as Aim, params: {} })),
          },
        })
      ),
    invalidate: [['wars']],
  })
  return (
    <Adjust
      title='Declare a war'
      note='Name the foe, the cause and the aims; each aim fills in its own terms.'
      label='Declare a war'
    >
      <FieldGrid>
        <EntityPicker
          label='Against'
          icon={Swords}
          types={COMMUNITIES}
          value={defender}
          onChange={setDefender}
          blocked={blocked}
        />
        <ChoiceField
          label='Cause'
          value={cause}
          table={CAUSE}
          blocked={blocked}
          onPick={setCause}
        />
        <TextField
          label='Proclamation'
          icon={ScrollText}
          value={reason}
          onChange={setReason}
          placeholder='What the proclamation says'
        />
      </FieldGrid>
      <Muted variant='caption'>Aims</Muted>
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
      <ActionButton
        label='Declare'
        icon={Swords}
        busy={busyOf(blocked, declare.isPending)}
        missing={defender ? undefined : 'Choose whom to fight'}
        onClick={() => declare.mutate()}
      />
    </Adjust>
  )
}
