import { useState } from 'react'
import {
  Baby,
  Dna,
  EyeOff,
  GitBranch,
  Heart,
  HeartCrack,
  Network,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { PLAN_STATUSES } from '@/features/cycles/labels'
import { clamp, SPAN } from '@/features/cycles/model'
import { TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type RegimeNodeView, useRegimeAction } from './api'
import { SEGMENT_LEVELS } from './labels'
import { useRegimeRow } from './model'

type Segment = RegimeNodeView['kin_lines'][number]
type Breeding = RegimeNodeView['breeding'][number]

const NOT_HOUSE = 'Only a house takes a place among the lines of its tribe'
const PLAN_STEPS = 100

function SegmentCard({
  row,
  blocked,
}: {
  row: Segment
  blocked: string | null
}) {
  const action = useRegimeRow(
    'kin_segment:edit',
    'kin_segment:delete',
    { house_id: row.house.id },
    blocked
  )
  const level = SEGMENT_LEVELS[row.level]
  return (
    <Held
      icon={level.icon}
      tone={level.tone}
      title={`${row.house.name}, a ${level.label.toLowerCase()}`}
      caption={`Since epoch ${row.since_epoch}`}
      removeLabel='Let it be read anew'
      editTitle='Set the place of the house'
      note='Lines nest within clans and clans within a tribe. In a feud each line backs the nearer kin, and against foreigners the whole tribe unites; every line that takes a side swells the feud.'
      fields={[
        {
          key: 'level',
          label: 'Place among the lines',
          kind: 'pick',
          table: table(SEGMENT_LEVELS),
        },
        {
          key: 'tribe_entity_id',
          label: 'Tribe',
          kind: 'node',
          types: ['people'],
        },
        {
          key: 'backs_entity_id',
          label: 'Backs in a feud',
          kind: 'node',
          types: ['house'],
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Tribe', <Ref key='tribe' node={row.tribe} empty='no tribe' />],
          [
            'Backs in a feud',
            <Ref key='backs' node={row.backs} empty='no one' />,
          ],
        ]}
      />
    </Held>
  )
}

function SegmentForge({
  nodeId,
  isHouse,
  blocked,
}: {
  nodeId: number
  isHouse: boolean
  blocked: string | null
}) {
  const [level, setLevel] = useState<keyof typeof SEGMENT_LEVELS>('lineage')
  const [tribe, setTribe] = useState<number | null>(null)
  const setting = useRegimeAction(
    'kin_segment:set',
    (_: void) => ({ house_id: nodeId, level, tribe_id: tribe }),
    'The house takes its place'
  )
  const busy = why(isHouse ? blocked : NOT_HOUSE, setting.isPending)
  return (
    <ForgeCard
      icon={Network}
      tone='gold'
      title='Place the house among the lines of its tribe'
      note='Choose whether it is a lineage, a clan or the tribe itself, and the people it belongs to.'
      columns={2}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Network />
          Place it
        </Button>
      }
    >
      <MindPicker
        label='Place'
        value={level}
        table={table(SEGMENT_LEVELS)}
        blocked={busy}
        onPick={(value) => setLevel(value as keyof typeof SEGMENT_LEVELS)}
      />
      <NodePicker
        label='Tribe'
        value={tribe}
        onChange={setTribe}
        blocked={busy}
        types={['people']}
      />
    </ForgeCard>
  )
}

function BreedingCard({
  row,
  blocked,
}: {
  row: Breeding
  blocked: string | null
}) {
  const action = useRegimeRow(
    'breeding:edit',
    'breeding:delete',
    { plan_id: row.plan_id },
    blocked
  )
  const aim =
    row.locus && row.allele
      ? `${row.allele} at ${row.locus.replace(/_/g, ' ')}`
      : 'a union with a claim'
  return (
    <Held
      icon={Dna}
      tone='verdigris'
      title={`${row.name}: ${row.house.name} bred toward ${aim}`}
      caption={`${row.progress} of ${plural(row.steps, 'step', 'steps')} · ${PLAN_STATUSES[row.status].label}`}
      removeLabel='End the design'
      editTitle='Set the breeding plan'
      note='The design steers the house’s marriages toward carriers of a trait of the blood or toward claimants of a realm. Love matches set it back, childless couples stall it, and each concealed parentage keeps it secret but becomes a secret of its own that can be exposed.'
      fields={[
        { key: 'locus', label: 'Trait of the blood', kind: 'text' },
        { key: 'allele', label: 'Form of the trait', kind: 'text' },
        {
          key: 'target_share',
          label: 'Share of the house to carry it (%)',
          kind: 'number',
          min: 1,
          max: SPAN,
        },
        {
          key: 'claim_polity_id',
          label: 'Realm whose claimants to marry',
          kind: 'node',
          types: ['polity'],
        },
        { key: 'matches', label: 'Matches made', kind: 'number', min: 0 },
        { key: 'love_matches', label: 'Love matches', kind: 'number', min: 0 },
        { key: 'barren', label: 'Childless couples', kind: 'number', min: 0 },
        {
          key: 'concealed',
          label: 'Concealed parentages',
          kind: 'number',
          min: 0,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Progress of the design'
        value={row.progress}
        max={Math.max(1, row.steps)}
        tone='verdigris'
        icon={Dna}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @xl/tiles:grid-cols-4'>
          <KpiTile
            label='Matches'
            value={row.matches}
            icon={Heart}
            tone='success'
          />
          <KpiTile
            label='Love matches'
            value={row.love_matches}
            icon={HeartCrack}
            tone='warning'
          />
          <KpiTile
            label='Childless'
            value={row.barren}
            icon={Baby}
            tone='muted'
          />
          <KpiTile
            label='Concealed'
            value={row.concealed}
            icon={EyeOff}
            tone='info'
          />
        </div>
      </div>
      <Facts
        items={[
          [
            'Held by',
            <Ref key='holder' node={row.holder} empty='no one living' />,
          ],
          ['House to carry it', `${row.target_share}%`],
          [
            'Claim sought',
            <Ref key='claim' node={row.claim_polity} empty='none' />,
          ],
        ]}
      />
    </Held>
  )
}

function BreedingForge({
  nodeId,
  isHouse,
  blocked,
}: {
  nodeId: number
  isHouse: boolean
  blocked: string | null
}) {
  const [holder, setHolder] = useState<number | null>(null)
  const [house, setHouse] = useState<number | null>(isHouse ? nodeId : null)
  const [name, setName] = useState('')
  const [locus, setLocus] = useState('')
  const [allele, setAllele] = useState('')
  const [claim, setClaim] = useState<number | null>(null)
  const [share, setShare] = useState('60')
  const [steps, setSteps] = useState('10')
  const creating = useRegimeAction(
    'breeding:create',
    (_: void) => ({
      holder_id: holder ?? 0,
      house_id: house ?? 0,
      name: name.trim(),
      locus: locus.trim() || null,
      allele: allele.trim() || null,
      claim_polity_id: claim,
      target_share: clamp(share, SPAN, 1),
      steps: clamp(steps, PLAN_STEPS, 1),
    }),
    'The design begins'
  )
  const aimless =
    (locus.trim() === '' || allele.trim() === '') && claim === null
  const reason =
    holder === null || house === null
      ? 'Choose who holds the design and the house it steers'
      : name.trim() === ''
        ? 'Name the design'
        : aimless
          ? 'Name a trait and its form, or a realm whose claimants to marry'
          : blocked
  const busy = why(reason, creating.isPending)
  return (
    <ForgeCard
      icon={Dna}
      tone='verdigris'
      title='Begin a design that steers a house’s marriages'
      note='Held by an order, a house or a god; it steers marriages across generations.'
      columns={4}
      action={
        <Button
          act={creating}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => creating.mutate()}
        >
          <Dna />
          Begin it
        </Button>
      }
    >
      <NodePicker
        label='Held by'
        value={holder}
        onChange={setHolder}
        blocked={blocked}
        types={['faction', 'cult', 'house', 'mortal', 'polity']}
        kinds={['son', 'foreign_god']}
      />
      <NodePicker
        label='House steered'
        value={house}
        onChange={setHouse}
        blocked={blocked}
        types={['house']}
      />
      <TextField
        label='Name of the design'
        value={name}
        blocked={blocked}
        onChange={setName}
      />
      <TextField
        label='Trait of the blood'
        value={locus}
        blocked={blocked}
        onChange={setLocus}
      />
      <TextField
        label='Form of the trait'
        value={allele}
        blocked={blocked}
        onChange={setAllele}
      />
      <NodePicker
        label='Realm whose claimants to marry'
        value={claim}
        onChange={setClaim}
        blocked={blocked}
        types={['polity']}
      />
      <NumberField
        label='Share to carry it (%)'
        value={share}
        min={1}
        max={SPAN}
        blocked={blocked}
        onChange={setShare}
      />
      <NumberField
        label='Steps'
        value={steps}
        min={1}
        max={PLAN_STEPS}
        blocked={blocked}
        onChange={setSteps}
      />
    </ForgeCard>
  )
}

export function LineagePanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: RegimeNodeView
  blocked: string | null
}) {
  const isHouse = kind === 'house'
  return (
    <div data-surface='LineagePanel' className='flex min-w-0 flex-col gap-4'>
      {data.lineage ? (
        <SegmentCard row={data.lineage} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          {isHouse
            ? 'This house has no place among the lines of a tribe yet.'
            : NOT_HOUSE}
        </Muted>
      )}
      <SegmentForge nodeId={nodeId} isHouse={isHouse} blocked={blocked} />
      <Listed
        title='Lines of the tribe and their backers'
        items={data.kin_lines}
        empty='No lines belong to this tribe or back this house.'
        noun={['line', 'lines']}
        itemKey={(item) => item.house.id}
      >
        {(item) => <SegmentCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Designs that steer marriages'
        items={data.breeding}
        empty='No design steers marriages here.'
        noun={['design', 'designs']}
        itemKey={(item) => item.plan_id}
      >
        {(item) => <BreedingCard row={item} blocked={blocked} />}
      </Listed>
      <BreedingForge nodeId={nodeId} isHouse={isHouse} blocked={blocked} />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Chip
          icon={GitBranch}
        >{`${plural(data.kin_lines.length, 'line', 'lines')} read here`}</Chip>
      </div>
    </div>
  )
}
