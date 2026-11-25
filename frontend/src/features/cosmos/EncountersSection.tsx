import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Anchor,
  CirclePlus,
  Clock,
  Cloud,
  Coins,
  Compass,
  Gift,
  Mountain,
  Network,
  Orbit,
  Pickaxe,
  Route,
  Swords,
  Thermometer,
  Trash2,
  TriangleAlert,
  UserMinus,
  Waves,
  Zap,
  Ship,
} from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import {
  EmptyState,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { table } from '@/features/arcana/labels'
import {
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { type Named } from '@/features/entity/environment/labels'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'

type Environment = components['schemas']['TradeMode']
type Effect = components['schemas']['EncounterEffect']
type Encounter = components['schemas']['JourneyEncounterView']
type Edit = { values: EditValues; release: string[] }

const SHOWN = 8
const HOLD =
  'Values you set are held against the engine until you release them.'

export const ENVIRONMENTS: Record<Environment, Named> = {
  road: { label: 'Road', icon: Mountain, tone: 'gold' },
  river: { label: 'River', icon: Waves, tone: 'info' },
  sea: { label: 'Sea', icon: Ship, tone: 'info' },
  sky: { label: 'Sky', icon: Cloud, tone: 'info' },
  space: { label: 'Space', icon: Orbit, tone: 'verdigris' },
  rift: { label: 'Rift', icon: Zap, tone: 'danger' },
  network: { label: 'Network', icon: Network, tone: 'muted' },
  underground: { label: 'Tunnel way', icon: Pickaxe, tone: 'muted' },
}

export const EFFECTS: Record<Effect, Named> = {
  attack: { label: 'An attack', icon: Swords, tone: 'danger' },
  hazard: { label: 'A hazard', icon: TriangleAlert, tone: 'warning' },
  delay: { label: 'A delay', icon: Clock, tone: 'muted' },
  straying: { label: 'Straying from the way', icon: Compass, tone: 'warning' },
  find: { label: 'A find', icon: Gift, tone: 'success' },
  toll: { label: 'A toll', icon: Coins, tone: 'gold' },
  sickness: { label: 'Sickness', icon: Thermometer, tone: 'danger' },
  desertion: { label: 'Desertion', icon: UserMinus, tone: 'warning' },
}

const FIELDS: readonly Field[] = [
  { key: 'name', label: 'What it is called', kind: 'text' },
  {
    key: 'environment',
    label: 'Where it happens',
    kind: 'pick',
    table: table(ENVIRONMENTS),
  },
  { key: 'effect', label: 'What it does', kind: 'pick', table: table(EFFECTS) },
  {
    key: 'weight',
    label: 'How often it comes',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'loss_pct',
    label: 'Share of travellers lost',
    kind: 'number',
    min: 0,
    max: 100,
  },
]

function useEncounters(worldId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'journey-encounters', worldId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/journey-encounters', {
          params: { query: { world_id: worldId } },
        })
      ),
  })
}

function EncounterRow({
  row,
  blocked,
}: {
  row: Encounter
  blocked: string | null
}) {
  const effect = EFFECTS[row.effect]
  const editing = useMadeAction(
    'journey_encounter:edit',
    (vars: Edit) => ({
      encounter_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The encounter is set so'
  )
  const removing = useMadeAction(
    'journey_encounter:delete',
    (_: void) => ({ encounter_id: row.id }),
    'The encounter is struck from the roads'
  )
  return (
    <RecordRow
      icon={effect.icon}
      tone={effect.tone ?? 'info'}
      title={`${row.name ?? effect.label} on ${ENVIRONMENTS[row.environment].label.toLowerCase()} roads`}
      caption={`weight ${row.weight}, ${row.loss_pct}% of travellers lost; ${row.world ? `only on ${row.world.name}` : 'on every world'}`}
    >
      <RecordEditor
        act={editing}
        title='Set the encounter'
        note={HOLD}
        fields={FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Strike it'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

export function EncountersSection({
  worldId,
  readOnlyReason = null,
}: {
  worldId: number
  readOnlyReason?: string | null
}) {
  const query = useEncounters(worldId)
  const shown = useShowMore(query.data ?? [], SHOWN, SHOWN)
  const [environment, setEnvironment] = useState<string>('land')
  const [effect, setEffect] = useState<string>('hazard')
  const [weight, setWeight] = useState('40')
  const [loss, setLoss] = useState('10')
  const creating = useMadeAction(
    'journey_encounter:create',
    (_: void) => ({
      world_id: worldId,
      environment: environment as Environment,
      effect: effect as Effect,
      weight: Math.min(100, Math.max(0, Number(weight) || 0)),
      loss_pct: Math.min(100, Math.max(0, Number(loss) || 0)),
    }),
    'A new encounter waits on the roads'
  )
  const blocked = readOnlyReason
  return (
    <Section
      id='section-encounters'
      title='Road encounters: what travellers meet on the way'
      description='Each kind of road (sea, land, air, space, rift, network) holds the encounters a journey may meet there: attacks, hazards, delays, straying, finds, tolls, sickness and desertion.'
      icon={Route}
      tone='info'
    >
      <div
        data-surface='EncountersSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the roads' />
        ) : query.isError ? (
          <EmptyState
            icon={Anchor}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : query.data.length ? (
          <>
            <ul className='flex min-w-0 flex-col gap-2'>
              {shown.visible.map((row) => (
                <EncounterRow key={row.id} row={row} blocked={blocked} />
              ))}
            </ul>
            <ShowMore state={shown} />
          </>
        ) : (
          <EmptyState
            icon={Route}
            size='inline'
            title='No encounters yet'
            description='The roads are given their encounters at the next epoch; add one below.'
          />
        )}
        <ForgeCard
          icon={CirclePlus}
          tone='info'
          title='Add an encounter for this world'
          note='A journey on such a road draws among its encounters by weight.'
          columns={4}
          action={
            <StepButton
              act={creating}
              icon={CirclePlus}
              label='Add it'
              variant='default'
              busy={why(blocked, creating.isPending)}
              onClick={() => creating.mutate()}
            />
          }
        >
          <ChoiceField
            label='Road'
            value={environment}
            table={ENVIRONMENTS}
            blocked={blocked}
            onPick={setEnvironment}
          />
          <ChoiceField
            label='What it does'
            value={effect}
            table={EFFECTS}
            blocked={blocked}
            onPick={setEffect}
          />
          <NumberField
            label='How often'
            value={weight}
            min={0}
            max={100}
            onChange={setWeight}
          />
          <NumberField
            label='Travellers lost (%)'
            value={loss}
            min={0}
            max={100}
            onChange={setLoss}
          />
        </ForgeCard>
      </div>
    </Section>
  )
}
