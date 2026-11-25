import { useState } from 'react'
import {
  Baby,
  BookOpen,
  Building2,
  Coins,
  Globe,
  HeartCrack,
  Hourglass,
  Scale,
  Sprout,
  Users,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { VALUE_ICONS } from '@/features/entity/mind/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { SEX_SPEC } from '@/features/entity/society/labels'
import { Ref } from '@/features/gatherings/parts'
import { type CollectiveView, useCollectiveAction } from './api'
import { FORMATIVE } from './labels'
import { clamp, SPAN, useRow } from './model'
import { Held, Listed } from './parts'

type Generation = CollectiveView['generations'][number]
type ValueAxis = components['schemas']['ValueAxis']
type Diaspora = CollectiveView['diasporas'][number]
type Transition = NonNullable<CollectiveView['transition']>
type Ratio = NonNullable<CollectiveView['sex_ratio']>

const NO_AXIS = 'none'
const AXIS_PICK = { [NO_AXIS]: 'No value', ...table(VALUE_ICONS) }

function GenerationCard({
  communityId,
  row,
  blocked,
}: {
  communityId: number
  row: Generation
  blocked: string | null
}) {
  const action = useRow(
    'generation:edit',
    'generation:delete',
    { community_id: communityId, generation_epoch: row.generation_epoch },
    blocked
  )
  const [formative, setFormative] =
    useState<keyof typeof FORMATIVE>('golden_age')
  const [axis, setAxis] = useState(NO_AXIS)
  const [shift, setShift] = useState('10')
  const shaping = useCollectiveAction(
    'generation:shape',
    (_: void) => ({
      community_id: communityId,
      generation_epoch: row.generation_epoch,
      formative: [...new Set([...row.formative, formative])],
      axis: axis === NO_AXIS ? null : (axis as ValueAxis),
      shift: clamp(shift, SPAN, -SPAN),
    }),
    'The generation is shaped so'
  )
  const busy = why(action.busy, shaping.isPending)
  const shifts = Object.entries(row.value_shifts)
  return (
    <Held
      icon={row.passed_epoch !== null ? Hourglass : Baby}
      tone={row.passed_epoch !== null ? 'muted' : 'info'}
      title={`The generation born from epoch ${row.generation_epoch}`}
      caption={
        row.passed_epoch !== null
          ? `Passed in epoch ${row.passed_epoch}`
          : `${row.alive} still living`
      }
      removeLabel='Strike from the record'
      editTitle='Set the generation'
      note='A generation carries what shaped its youth into its people’s values; when it passes, its children keep only part of it.'
      fields={[
        { key: 'alive', label: 'Still living', kind: 'number', min: 0 },
        {
          key: 'passed_epoch',
          label: 'Passed in epoch',
          kind: 'number',
          min: 0,
        },
      ]}
      locked={row.locked}
      blocked={busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='flex min-w-0 flex-wrap gap-2'>
        {row.formative.length === 0 ? (
          <Chip>Nothing great shaped its youth</Chip>
        ) : (
          row.formative.map((item) => (
            <Chip key={item} icon={FORMATIVE[item].icon}>
              {FORMATIVE[item].label}
            </Chip>
          ))
        )}
      </div>
      <Facts
        items={
          shifts.length === 0
            ? [['Values it carries', 'none']]
            : shifts.map(([key, value]): [string, string] => [
                VALUE_ICONS[key]?.label ?? key,
                `${value > 0 ? '+' : ''}${value}`,
              ])
        }
      />
      <div className='grid min-w-0 gap-2 sm:grid-cols-4'>
        <MindPicker
          label='Shaped also by'
          value={formative}
          table={table(FORMATIVE)}
          blocked={busy}
          onPick={(value) => setFormative(value as keyof typeof FORMATIVE)}
        />
        <MindPicker
          label='Value it moved'
          value={axis}
          table={AXIS_PICK}
          blocked={busy}
          onPick={setAxis}
        />
        <NumberField
          label='By'
          value={shift}
          min={-SPAN}
          max={SPAN}
          blocked={busy}
          onChange={setShift}
        />
        <Button
          act={shaping}
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => shaping.mutate()}
        >
          <Sprout />
          Shape it
        </Button>
      </div>
    </Held>
  )
}

function GenerationForge({
  communityId,
  isTown,
  blocked,
}: {
  communityId: number
  isTown: boolean
  blocked: string | null
}) {
  const [epoch, setEpoch] = useState('0')
  const setting = useCollectiveAction(
    'generation:set',
    (_: void) => ({
      community_id: communityId,
      generation_epoch: clamp(epoch, 100_000),
    }),
    'The generation is recorded'
  )
  const busy = why(
    isTown ? blocked : 'Generations are counted in towns',
    setting.isPending
  )
  return (
    <ForgeCard
      icon={Baby}
      tone='info'
      title='Record a generation'
      note='Name the epoch a generation was born in; then set what shaped its youth.'
      columns={2}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Baby />
          Record it
        </Button>
      }
    >
      <NumberField
        label='Born from epoch'
        value={epoch}
        min={0}
        blocked={busy}
        onChange={setEpoch}
      />
    </ForgeCard>
  )
}

function DiasporaCard({
  row,
  blocked,
}: {
  row: Diaspora
  blocked: string | null
}) {
  const action = useRow(
    'diaspora:edit',
    'diaspora:delete',
    { people_id: row.people.id, host_id: row.host.id },
    blocked
  )
  return (
    <Held
      icon={Globe}
      tone='verdigris'
      title={`${row.people.name} in ${row.host.name}`}
      caption={`Since epoch ${row.since_epoch}`}
      removeLabel='Strike from the record'
      editTitle='Set the diaspora'
      note='Ties draw more of their people after them and send coin home; when ties fade, they become one with their hosts.'
      fields={[
        { key: 'population', label: 'People', kind: 'number', min: 0 },
        {
          key: 'ties',
          label: 'Ties to home',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'remittance',
          label: 'Sent home last epoch',
          kind: 'number',
          min: 0,
        },
        {
          key: 'home_entity_id',
          label: 'Homeland',
          kind: 'node',
          types: ['settlement', 'region', 'polity'],
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Ties to home'
        value={row.ties}
        max={SPAN}
        tone='verdigris'
        icon={Globe}
      />
      <Facts
        items={[
          ['People', row.population],
          ['Sent home', row.remittance],
          ['Home', <Ref key='home' node={row.home} empty='no homeland' />],
        ]}
      />
    </Held>
  )
}

function DiasporaForge({
  nodeId,
  type,
  blocked,
}: {
  nodeId: number
  type: string | null
  blocked: string | null
}) {
  const [other, setOther] = useState<number | null>(null)
  const [population, setPopulation] = useState('200')
  const isPeople = type === 'people'
  const setting = useCollectiveAction(
    'diaspora:set',
    (_: void) => ({
      people_id: isPeople ? nodeId : (other ?? 0),
      host_id: isPeople ? (other ?? 0) : nodeId,
      population: clamp(population, 1_000_000),
    }),
    'The diaspora is settled'
  )
  const wrong =
    type !== 'people' && type !== 'settlement'
      ? 'A diaspora joins a people to a town'
      : null
  const busy = why(
    wrong ??
      (other === null
        ? isPeople
          ? 'Choose the town they settle in'
          : 'Choose the people who settle here'
        : blocked),
    setting.isPending
  )
  return (
    <ForgeCard
      icon={Globe}
      tone='verdigris'
      title='Settle a diaspora'
      note='Plant a people in a foreign town; chain migration follows its ties.'
      columns={2}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Globe />
          Settle them
        </Button>
      }
    >
      <NodePicker
        label={isPeople ? 'Host town' : 'Settling people'}
        value={other}
        onChange={setOther}
        blocked={wrong ?? blocked}
        types={[isPeople ? 'settlement' : 'people']}
      />
      <NumberField
        label='How many settle'
        value={population}
        min={0}
        blocked={wrong ?? blocked}
        onChange={setPopulation}
      />
    </ForgeCard>
  )
}

function TransitionCard({
  communityId,
  row,
  blocked,
}: {
  communityId: number
  row: Transition
  blocked: string | null
}) {
  const action = useRow(
    'transition:edit',
    'transition:delete',
    { community_id: communityId },
    blocked
  )
  return (
    <Held
      icon={Building2}
      tone='info'
      title='Demographic transition'
      caption='Towns, letters and the schooling of those who bear young lower births slowly; an ageing people raises smaller levies.'
      removeLabel='Read it anew'
      editTitle='Set the transition'
      note='Fertility is against the usual hundred.'
      fields={[
        {
          key: 'fertility_pct',
          label: 'Fertility (%)',
          kind: 'number',
          min: 0,
          max: 200,
        },
        {
          key: 'elder_share',
          label: 'Elders (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'urban_share',
          label: 'Living in towns (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'literacy',
          label: 'Lettered (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @2xl/tiles:grid-cols-4'>
          <KpiTile
            label='Fertility'
            value={`${row.fertility_pct}%`}
            icon={Baby}
            tone='success'
          />
          <KpiTile
            label='Elders'
            value={`${row.elder_share}%`}
            icon={Hourglass}
            tone='muted'
          />
          <KpiTile
            label='In towns'
            value={`${row.urban_share}%`}
            icon={Building2}
            tone='info'
          />
          <KpiTile
            label='Lettered'
            value={`${row.literacy}%`}
            icon={BookOpen}
            tone='gold'
          />
        </div>
      </div>
    </Held>
  )
}

function RatioCard({
  communityId,
  row,
  blocked,
}: {
  communityId: number
  row: Ratio
  blocked: string | null
}) {
  const action = useRow(
    'sex_ratio:edit',
    'sex_ratio:delete',
    { community_id: communityId },
    blocked
  )
  return (
    <Held
      icon={Scale}
      tone={
        row.begetters_per_hundred < 85 || row.begetters_per_hundred > 118
          ? 'warning'
          : 'success'
      }
      title='Balance of the sexes'
      caption='After wars a skewed people marries late, takes several spouses where allowed, and may open its roles.'
      removeLabel='Count it anew'
      editTitle='Set the balance'
      note='Grown begetters per hundred grown bearers, where the biology has those two.'
      fields={[
        {
          key: 'begetters_per_hundred',
          label: 'Begetters per hundred bearers',
          kind: 'number',
          min: 0,
          max: 1000,
        },
        {
          key: 'bereaved_partners',
          label: 'Bereaved partners',
          kind: 'number',
          min: 0,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <KpiTile
          label='Begetters per hundred bearers'
          value={row.begetters_per_hundred}
          icon={Users}
          tone='info'
        />
        <KpiTile
          label='Bereaved partners'
          value={row.bereaved_partners}
          icon={HeartCrack}
          tone='muted'
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        {row.counts.length === 0 ? (
          <Muted variant='caption'>No grown folk counted yet.</Muted>
        ) : (
          row.counts.map((item) => (
            <Badge key={item.sex_kind} size='sm' variant='secondary'>
              {`${SEX_SPEC[item.sex_kind].label}: ${formatInteger(item.count)}`}
            </Badge>
          ))
        )}
      </div>
    </Held>
  )
}

function CommunityForge({
  communityId,
  type,
  blocked,
}: {
  communityId: number
  type: string | null
  blocked: string | null
}) {
  const [fertility, setFertility] = useState('100')
  const [begetters, setBegetters] = useState('100')
  const [bereaved, setBereaved] = useState('0')
  const wrong =
    type !== 'people' && type !== 'settlement'
      ? 'Only a town or people has a demography'
      : null
  const transition = useCollectiveAction(
    'transition:set',
    (_: void) => ({
      community_id: communityId,
      fertility_pct: clamp(fertility, 200),
    }),
    'Set so'
  )
  const ratio = useCollectiveAction(
    'sex_ratio:set',
    (_: void) => ({
      community_id: communityId,
      begetters_per_hundred: clamp(begetters, 1000),
      bereaved_partners: clamp(bereaved, 100000),
    }),
    'Set so'
  )
  const busy = why(wrong ?? blocked, transition.isPending, ratio.isPending)
  return (
    <ForgeCard
      icon={Coins}
      tone='info'
      title='Set the demography'
      note='Fix this community’s fertility or its balance of the sexes; the engine reads them anew each epoch unless held.'
      columns={2}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            act={transition}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => transition.mutate()}
          >
            <Baby />
            Set fertility
          </Button>
          <Button
            act={ratio}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => ratio.mutate()}
          >
            <Scale />
            Set the balance
          </Button>
        </div>
      }
    >
      <NumberField
        label='Fertility (%)'
        value={fertility}
        min={0}
        max={200}
        blocked={busy}
        onChange={setFertility}
      />
      <NumberField
        label='Begetters per hundred bearers'
        value={begetters}
        min={0}
        max={1000}
        blocked={busy}
        onChange={setBegetters}
      />
      <NumberField
        label='Bereaved partners'
        value={bereaved}
        min={0}
        max={100000}
        blocked={busy}
        onChange={setBereaved}
      />
    </ForgeCard>
  )
}

export function GenerationPanel({
  nodeId,
  type,
  data,
  blocked,
}: {
  nodeId: number
  type: string | null
  data: CollectiveView
  blocked: string | null
}) {
  return (
    <div
      id='section-generations'
      data-surface='GenerationPanel'
      className='flex min-w-0 flex-col gap-3'
    >
      <Label variant='overline'>Generations and people</Label>
      <Listed
        title='Generations'
        items={data.generations}
        empty='No generation is recorded here.'
        noun={['generation', 'generations']}
        itemKey={(row) => row.generation_epoch}
      >
        {(row) => (
          <GenerationCard communityId={nodeId} row={row} blocked={blocked} />
        )}
      </Listed>
      <GenerationForge
        communityId={nodeId}
        isTown={type === 'settlement'}
        blocked={blocked}
      />
      <Listed
        title='Diasporas'
        items={data.diasporas}
        empty='No people lives abroad here.'
        noun={['diaspora', 'diasporas']}
        itemKey={(row) => `${row.people.id}-${row.host.id}`}
      >
        {(row) => <DiasporaCard row={row} blocked={blocked} />}
      </Listed>
      <DiasporaForge nodeId={nodeId} type={type} blocked={blocked} />
      {data.transition && (
        <TransitionCard
          communityId={nodeId}
          row={data.transition}
          blocked={blocked}
        />
      )}
      {data.sex_ratio && (
        <RatioCard
          communityId={nodeId}
          row={data.sex_ratio}
          blocked={blocked}
        />
      )}
      <CommunityForge communityId={nodeId} type={type} blocked={blocked} />
    </div>
  )
}
