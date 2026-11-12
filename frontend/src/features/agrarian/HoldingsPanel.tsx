import { useState } from 'react'
import {
  Axe,
  Bird,
  Coins,
  Fence,
  HeartPulse,
  Package,
  Sprout,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { clamp, MANY, SPAN } from '@/features/cycles/model'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type AgrarianNodeView, useAgrarianAction } from './api'
import { COMMONS_KINDS, COMMONS_RULES, PERENNIALS } from './labels'
import {
  HOLDER_TYPES,
  TOWN_TYPES,
  useAgrarianRow,
  useAgrarianStep,
} from './model'

type Planting = AgrarianNodeView['perennials'][number]
type Common = AgrarianNodeView['commons'][number]
type Reserve = AgrarianNodeView['reserves'][number]
type Lore = NonNullable<AgrarianNodeView['famine']>

const NOT_LAND = 'Only a land holds plantings, commons and game'
const NOT_PEOPLE = 'Only a people remembers its hungry years'
const SPECIES = ['species'] as const

function PlantingCard({
  row,
  blocked,
}: {
  row: Planting
  blocked: string | null
}) {
  const action = useAgrarianRow(
    'perennial:edit',
    'perennial:delete',
    { perennial_id: row.id },
    blocked
  )
  const felling = useAgrarianStep(
    'perennial:fell',
    { perennial_id: row.id },
    blocked,
    'Cut down'
  )
  const kind = PERENNIALS[row.kind]
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={`${kind.label} in ${row.region.name}`}
      caption={`Planted in epoch ${row.planted_epoch}${row.felled_epoch !== null ? ` · cut down in epoch ${row.felled_epoch}` : ''}`}
      removeLabel='Remove the planting'
      editTitle='Set the planting'
      note='Long-lived plantings bear only after epochs, then pay their owner each epoch and lift the prosperity of their land; in old age they wear out and are planted anew. Armies that plunder a land cut some of them down, and those that lay it waste cut half, and they take generations to grow again.'
      fields={[
        {
          key: 'kind',
          label: 'Kind of planting',
          kind: 'pick',
          table: table(PERENNIALS),
        },
        {
          key: 'species_entity_id',
          label: 'Plant',
          kind: 'node',
          types: SPECIES,
        },
        {
          key: 'owner_node_id',
          label: 'Owner',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        {
          key: 'area',
          label: 'Share of the land',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'maturity',
          label: 'Grown (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'mature_epochs',
          label: 'Epochs to bear',
          kind: 'number',
          min: 1,
          max: SPAN,
        },
        {
          key: 'condition',
          label: 'Condition',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <StepButton
          icon={Axe}
          label='Cut it down'
          busy={felling.busy}
          onClick={felling.run}
        />
      }
    >
      <Meter label='Grown' value={row.maturity} tone='success' icon={Sprout} />
      <Meter
        label='Condition'
        value={row.condition}
        tone='verdigris'
        icon={HeartPulse}
      />
      <Facts
        items={[
          ['Plant', <Ref key='plant' node={row.species} empty='not named' />],
          ['Owner', <Ref key='owner' node={row.owner} empty='no owner' />],
          ['Share of the land', String(row.area)],
          ['Epochs to bear', String(row.mature_epochs)],
        ]}
      />
    </Held>
  )
}

function CommonCard({
  row,
  nodeId,
  blocked,
}: {
  row: Common
  nodeId: number
  blocked: string | null
}) {
  const action = useAgrarianRow(
    'commons:edit',
    'commons:delete',
    { commons_id: row.id },
    blocked
  )
  const [encloser, setEncloser] = useState<number | null>(nodeId)
  const enclosing = useAgrarianAction(
    'commons:enclose',
    (_: void) => ({ commons_id: row.id, encloser_id: encloser ?? 0 }),
    'The common is enclosed'
  )
  const kind = COMMONS_KINDS[row.kind]
  const rule = COMMONS_RULES[row.rule]
  const closing = why(
    row.rule === 'enclosed'
      ? 'It is already enclosed'
      : encloser === null
        ? 'Choose who encloses it'
        : blocked,
    enclosing.isPending
  )
  return (
    <Held
      icon={kind.icon}
      tone={rule.tone}
      title={`Common ${kind.label.toLowerCase()} of ${row.region.name}`}
      caption={`${rule.label} · since epoch ${row.since_epoch}`}
      removeLabel='Remove the common'
      editTitle='Set the common'
      note='Folk use their commons by custom. Use beyond what a common bears wears it down unless a council rules it. A ruler orders enclosure by mandate, sooner under a law of freehold and seldom under communal tenure; it pays the encloser but takes the living and wealth of cottager households, who drift to the cities and grow restless.'
      fields={[
        {
          key: 'kind',
          label: 'Kind of common',
          kind: 'pick',
          table: table(COMMONS_KINDS),
        },
        {
          key: 'rule',
          label: 'Held by',
          kind: 'pick',
          table: table(COMMONS_RULES),
        },
        {
          key: 'condition',
          label: 'Condition',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'use', label: 'Use', kind: 'number', min: 0, max: SPAN * 2 },
        {
          key: 'steward_entity_id',
          label: 'Steward town',
          kind: 'node',
          types: TOWN_TYPES,
        },
        {
          key: 'encloser_node_id',
          label: 'Encloser',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        {
          key: 'dispossessed',
          label: 'Folk driven off',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <NodePicker
            label='Encloser'
            value={encloser}
            onChange={setEncloser}
            blocked={blocked}
            types={HOLDER_TYPES}
          />
          <Button
            size='sm'
            variant='secondary'
            disabled={closing !== null}
            disabledReason={closing ?? undefined}
            onClick={() => enclosing.mutate()}
          >
            <Fence />
            Enclose it
          </Button>
        </div>
      }
    >
      <Meter
        label='Condition'
        value={row.condition}
        tone='success'
        icon={Sprout}
      />
      <Meter
        label='Use'
        value={Math.min(SPAN, row.use)}
        tone='warning'
        icon={Users}
      />
      <Facts
        items={[
          [
            'Steward',
            <Ref key='steward' node={row.steward} empty='no steward' />,
          ],
          [
            'Encloser',
            <Ref key='encloser' node={row.encloser} empty='not enclosed' />,
          ],
          [
            'Enclosed in epoch',
            row.enclosed_epoch !== null ? String(row.enclosed_epoch) : 'never',
          ],
          ['Folk driven off', String(row.dispossessed)],
        ]}
      />
    </Held>
  )
}

function ReserveCard({
  row,
  blocked,
}: {
  row: Reserve
  blocked: string | null
}) {
  const action = useAgrarianRow(
    'game_reserve:edit',
    'game_reserve:delete',
    { reserve_id: row.id },
    blocked
  )
  return (
    <Held
      icon={Bird}
      tone='verdigris'
      title={`Game reserve of ${row.region.name}`}
      caption={`Since epoch ${row.since_epoch}`}
      removeLabel='Lift the game laws'
      editTitle='Set the reserve'
      note='A reserve keeps the hunting for its holder and shields its beasts from the folk. Hunger and poverty breed poaching, which raises crime; a strict holder brings poachers to trial and the folk resent it.'
      fields={[
        {
          key: 'holder_node_id',
          label: 'Holder',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        {
          key: 'species_entity_id',
          label: 'Beast protected',
          kind: 'node',
          types: SPECIES,
        },
        {
          key: 'strictness',
          label: 'Strictness',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'poaching',
          label: 'Poaching',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'resentment',
          label: 'Resentment',
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
      <Meter
        label='Strictness'
        value={row.strictness}
        tone='info'
        icon={Fence}
      />
      <Meter label='Poaching' value={row.poaching} tone='warning' icon={Bird} />
      <Meter
        label='Resentment'
        value={row.resentment}
        tone='destructive'
        icon={Users}
      />
      <Facts
        items={[
          ['Holder', <Ref key='holder' node={row.holder} empty='no holder' />],
          [
            'Beast protected',
            <Ref key='beast' node={row.species} empty='all game' />,
          ],
        ]}
      />
    </Held>
  )
}

function LoreCard({ row, blocked }: { row: Lore; blocked: string | null }) {
  const action = useAgrarianRow(
    'famine_lore:edit',
    'famine_lore:delete',
    { people_id: row.people.id },
    blocked
  )
  return (
    <Held
      icon={Package}
      tone='gold'
      title={`What ${row.people.name} remember of hunger`}
      caption={`Read in epoch ${row.updated_epoch}`}
      removeLabel='Read their memory anew'
      editTitle='Set the famine lore'
      note='A people that remembers hungry years, and whose living generations were formed by famine, learns what the land gives in a failed year and stores food against the next. Famine foods and stores make good part of a failed harvest, but living on famine foods sickens the land.'
      fields={[
        {
          key: 'memory',
          label: 'Memory of hunger',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'famine_foods',
          label: 'Knows famine foods',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'storage',
          label: 'Storing food',
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
        <div className='grid min-w-0 grid-cols-1 gap-2 @lg/tiles:grid-cols-3'>
          <KpiTile
            label='Memory of hunger'
            value={row.memory}
            icon={HeartPulse}
            tone='danger'
          />
          <KpiTile
            label='Famine foods'
            value={row.famine_foods ? 'Known' : 'Unknown'}
            icon={Sprout}
            tone='success'
          />
          <KpiTile
            label='Storing food'
            value={row.storage}
            icon={Package}
            tone='gold'
          />
        </div>
      </div>
    </Held>
  )
}

function HoldingsForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const isLand = kind === 'region'
  const gate = isLand ? blocked : NOT_LAND
  const [plantKind, setPlantKind] = useState<keyof typeof PERENNIALS>('orchard')
  const [plant, setPlant] = useState<number | null>(null)
  const [owner, setOwner] = useState<number | null>(null)
  const [area, setArea] = useState('5')
  const [commonKind, setCommonKind] =
    useState<keyof typeof COMMONS_KINDS>('pasture')
  const [rule, setRule] = useState<keyof typeof COMMONS_RULES>('customary')
  const [holder, setHolder] = useState<number | null>(null)
  const [strictness, setStrictness] = useState('60')
  const planting = useAgrarianAction(
    'perennial:plant',
    (_: void) => ({
      region_id: nodeId,
      kind: plantKind,
      species_id: plant,
      owner_id: owner,
      area: clamp(area) || 1,
    }),
    'Planted'
  )
  const opening = useAgrarianAction(
    'commons:create',
    (_: void) => ({ region_id: nodeId, kind: commonKind, rule }),
    'A common is held'
  )
  const reserving = useAgrarianAction(
    'game_reserve:declare',
    (_: void) => ({
      region_id: nodeId,
      holder_id: holder ?? 0,
      species_id: plant,
      strictness: clamp(strictness),
    }),
    'The game is reserved'
  )
  const plantBusy = why(gate, planting.isPending)
  const commonBusy = why(gate, opening.isPending)
  const reserveBusy = why(
    isLand
      ? holder === null
        ? 'Choose a holder for the reserve'
        : blocked
      : NOT_LAND,
    reserving.isPending
  )
  return (
    <ForgeCard
      icon={Sprout}
      tone='success'
      title='Plant, hold in common or reserve'
      note='Set a long-lived planting in this land, give its folk a common, or reserve its game for a holder. The plant chosen is also the beast a reserve protects when you reserve.'
      columns={4}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={plantBusy !== null}
            disabledReason={plantBusy ?? undefined}
            onClick={() => planting.mutate()}
          >
            <Sprout />
            Plant it
          </Button>
          <Button
            size='sm'
            variant='secondary'
            disabled={commonBusy !== null}
            disabledReason={commonBusy ?? undefined}
            onClick={() => opening.mutate()}
          >
            <Users />
            Hold it in common
          </Button>
          <Button
            size='sm'
            variant='secondary'
            disabled={reserveBusy !== null}
            disabledReason={reserveBusy ?? undefined}
            onClick={() => reserving.mutate()}
          >
            <Bird />
            Reserve the game
          </Button>
        </div>
      }
    >
      <MindPicker
        label='Kind of planting'
        value={plantKind}
        table={table(PERENNIALS)}
        blocked={gate}
        onPick={(value) => setPlantKind(value as keyof typeof PERENNIALS)}
      />
      <NodePicker
        label='Plant or beast'
        value={plant}
        onChange={setPlant}
        blocked={gate}
        types={SPECIES}
      />
      <NodePicker
        label='Owner of the planting'
        value={owner}
        onChange={setOwner}
        blocked={gate}
        types={HOLDER_TYPES}
      />
      <NumberField
        label='Share of the land'
        value={area}
        min={1}
        max={SPAN}
        blocked={gate}
        onChange={setArea}
      />
      <MindPicker
        label='Kind of common'
        value={commonKind}
        table={table(COMMONS_KINDS)}
        blocked={gate}
        onPick={(value) => setCommonKind(value as keyof typeof COMMONS_KINDS)}
      />
      <MindPicker
        label='Held by'
        value={rule}
        table={table(COMMONS_RULES)}
        blocked={gate}
        onPick={(value) => setRule(value as keyof typeof COMMONS_RULES)}
      />
      <NodePicker
        label='Holder of the reserve'
        value={holder}
        onChange={setHolder}
        blocked={gate}
        types={HOLDER_TYPES}
      />
      <NumberField
        label='Strictness'
        value={strictness}
        min={0}
        max={SPAN}
        blocked={gate}
        onChange={setStrictness}
      />
    </ForgeCard>
  )
}

function LoreForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const gate = kind === 'people' ? blocked : NOT_PEOPLE
  const [memory, setMemory] = useState('50')
  const [foods, setFoods] = useState<'true' | 'false'>('true')
  const [storage, setStorage] = useState('40')
  const setting = useAgrarianAction(
    'famine_lore:set',
    (_: void) => ({
      people_id: nodeId,
      memory: clamp(memory),
      famine_foods: foods === 'true',
      storage: clamp(storage),
    }),
    'The famine lore is set'
  )
  const busy = why(gate, setting.isPending)
  return (
    <ForgeCard
      icon={Coins}
      tone='gold'
      title='Set what the people remember of hunger'
      note='Give a people its memory of hungry years, its famine foods and its tradition of storing food.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Package />
          Set it
        </Button>
      }
    >
      <NumberField
        label='Memory of hunger'
        value={memory}
        min={0}
        max={SPAN}
        blocked={gate}
        onChange={setMemory}
      />
      <MindPicker
        label='Knows famine foods'
        value={foods}
        table={YES_NO}
        blocked={gate}
        onPick={(value) => setFoods(value as 'true' | 'false')}
      />
      <NumberField
        label='Storing food'
        value={storage}
        min={0}
        max={SPAN}
        blocked={gate}
        onChange={setStorage}
      />
    </ForgeCard>
  )
}

export function HoldingsPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: AgrarianNodeView
  blocked: string | null
}) {
  return (
    <div data-surface='HoldingsPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Long-lived plantings'
        items={data.perennials}
        empty='No orchards, vineyards, groves or timber stand here.'
        noun={['planting', 'plantings']}
        itemKey={(item) => item.id}
      >
        {(item) => <PlantingCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Commons'
        items={data.commons}
        empty='No common is held here.'
        noun={['common', 'commons']}
        itemKey={(item) => item.id}
      >
        {(item) => <CommonCard row={item} nodeId={nodeId} blocked={blocked} />}
      </Listed>
      <Listed
        title='Game reserves'
        items={data.reserves}
        empty='No game is reserved here.'
        noun={['reserve', 'reserves']}
        itemKey={(item) => item.id}
      >
        {(item) => <ReserveCard row={item} blocked={blocked} />}
      </Listed>
      <HoldingsForge nodeId={nodeId} kind={kind} blocked={blocked} />
      <Listed
        title='Famine lore'
        items={data.famine ? [data.famine] : []}
        empty='No memory of hunger is kept here.'
        noun={['people', 'peoples']}
        itemKey={(item) => item.people.id}
      >
        {(item) => <LoreCard row={item} blocked={blocked} />}
      </Listed>
      <LoreForge nodeId={nodeId} kind={kind} blocked={blocked} />
    </div>
  )
}
