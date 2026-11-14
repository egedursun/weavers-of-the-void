import { useState } from 'react'
import { Beer, HandHeart, Home, Plus, Route, Users } from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type CustomsNodeView, useCustomsAction } from './api'
import { PURPOSES } from './labels'
import {
  MANY,
  MORTAL_TYPES,
  SPAN,
  useCustomsRow,
  useCustomsStep,
} from './model'

type View = CustomsNodeView
type Tavern = View['taverns'][number]
type Welfare = View['welfare'][number]
type Commute = NonNullable<View['commute']>
type Coop = NonNullable<View['cooperative']>

const STRUCTURES = ['structure'] as const

function TavernCard({ row, blocked }: { row: Tavern; blocked: string | null }) {
  const action = useCustomsRow(
    'tavern:edit',
    'tavern:delete',
    { structure_id: row.structure.id },
    blocked
  )
  return (
    <Held
      icon={Beer}
      tone='gold'
      title={row.structure.name}
      caption={`${plural(row.patrons, 'patron', 'patrons')} · ${plural(row.rumours, 'rumour', 'rumours')} · ${plural(row.brawls, 'brawl', 'brawls')} · lodges ${row.lodging}`}
      removeLabel='Strike the tavern'
      editTitle='Set the tavern'
      note='A tavern draws rumours to its town, and its keeper gains renown from the news that passes; drink breeds brawls, and an inn lodges travellers and brings trade.'
      fields={[
        {
          key: 'keeper_node_id',
          label: 'Keeper',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        { key: 'patrons', label: 'Patrons', kind: 'number', min: 0, max: MANY },
        { key: 'brawls', label: 'Brawls', kind: 'number', min: 0, max: MANY },
        { key: 'lodging', label: 'Lodging', kind: 'number', min: 0, max: MANY },
        { key: 'rumours', label: 'Rumours', kind: 'number', min: 0, max: MANY },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Keeper', <Ref key='keeper' node={row.keeper} empty='no keeper' />],
        ]}
      />
    </Held>
  )
}

function WelfareCard({
  row,
  blocked,
}: {
  row: Welfare
  blocked: string | null
}) {
  const action = useCustomsRow(
    'welfare_house:edit',
    'welfare_house:delete',
    { structure_id: row.structure.id },
    blocked
  )
  return (
    <Held
      icon={HandHeart}
      tone='success'
      title={row.structure.name}
      caption={`${row.inmates} taken in · upkeep ${row.upkeep}`}
      removeLabel='Strike the house'
      editTitle='Set the house of welfare'
      note="A house of welfare eases its town's poverty and keeps beggars from its streets; its patron gains renown."
      fields={[
        {
          key: 'patron_node_id',
          label: 'Patron',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'inmates',
          label: 'Taken in',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'upkeep', label: 'Upkeep', kind: 'number', min: 0, max: MANY },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Patron', <Ref key='patron' node={row.patron} empty='no patron' />],
        ]}
      />
    </Held>
  )
}

function CommuteCard({
  town,
  row,
  blocked,
}: {
  town: number
  row: Commute
  blocked: string | null
}) {
  const action = useCustomsRow(
    'commute:edit',
    'commute:delete',
    { settlement_id: town },
    blocked
  )
  return (
    <Held
      icon={Route}
      tone='info'
      title={`The way to work: ${row.distance}`}
      caption={`${row.labour_lost}% of labour lost${row.worker_camp ? ' · a worker camp' : ''} · read in epoch ${row.updated_epoch}`}
      removeLabel='Forget the way to work'
      editTitle='Set the way to work'
      note='Districts lengthen the way to work and roads and bridges shorten it; labour lost on the way is lost at the mines and fields, and a worker camp wins half of it back.'
      fields={[
        {
          key: 'distance',
          label: 'Distance',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'labour_lost',
          label: 'Labour lost (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'worker_camp',
          label: 'Worker camp',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Labour lost (${row.labour_lost} of ${SPAN})`}
        value={row.labour_lost}
        tone='warning'
        icon={Route}
      />
    </Held>
  )
}

function CoopCard({
  faction,
  row,
  blocked,
}: {
  faction: number
  row: Coop
  blocked: string | null
}) {
  const action = useCustomsRow(
    'cooperative:edit',
    'cooperative:delete',
    { faction_id: faction },
    blocked
  )
  const purpose = PURPOSES[row.purpose]
  return (
    <Held
      icon={purpose.icon}
      tone={purpose.tone}
      title={`A cooperative for ${purpose.label.toLowerCase()}`}
      caption={`${plural(row.members, 'member', 'members')} · pool ${row.pool}`}
      removeLabel='Undo the cooperative'
      editTitle='Set the cooperative'
      note='Members pool their means: a mill, boats or irrigation raise the town, insurance, burial and credit ease its want.'
      fields={[
        {
          key: 'purpose',
          label: 'Purpose',
          kind: 'pick',
          table: table(PURPOSES),
        },
        { key: 'pool', label: 'Pool', kind: 'number', min: 0, max: MANY },
        { key: 'members', label: 'Members', kind: 'number', min: 0, max: MANY },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

export function TownPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: View
  blocked: string | null
}) {
  const [structure, setStructure] = useState<number | null>(
    kind === 'structure' ? nodeId : null
  )
  const [purpose, setPurpose] = useState('mill')
  const town = kind === 'settlement'
  const faction = kind === 'faction'
  const tavern = useCustomsAction(
    'tavern:set',
    (_: void) => ({ structure_id: structure ?? 0, keeper_node_id: null }),
    'The tavern is kept'
  )
  const house = useCustomsAction(
    'welfare_house:set',
    (_: void) => ({ structure_id: structure ?? 0, patron_node_id: null }),
    'The house takes in the poor'
  )
  const way = useCustomsAction(
    'commute:set',
    (_: void) => ({ settlement_id: nodeId, distance: 10 }),
    'The way to work is set'
  )
  const pool = useCustomsAction(
    'cooperative:set',
    (_: void) => ({ faction_id: nodeId, purpose: purpose as Coop['purpose'] }),
    'The members pool their means'
  )
  const tending = useCustomsStep(
    'town_life:run',
    {},
    blocked,
    'Town life is tended'
  )
  const structureBusy = why(
    blocked ?? (structure === null ? 'Choose a building' : null),
    tavern.isPending,
    house.isPending
  )
  const wayBusy = why(
    blocked ??
      (!town
        ? 'Only a town has a way to work'
        : data.commute
          ? 'Its way to work is read; adjust it above'
          : null),
    way.isPending
  )
  const poolBusy = why(
    blocked ??
      (!faction
        ? 'Only a faction pools its means'
        : data.cooperative
          ? 'It pools already; adjust it above'
          : null),
    pool.isPending
  )
  return (
    <div data-surface='TownLifePanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-town-life'
        title='Taverns and houses of welfare'
        legend={[
          { text: 'Patrons', variant: 'warning' },
          { text: 'Taken in', variant: 'success' },
        ]}
        rows={[
          ...data.taverns.map((row) => ({
            key: `t${row.structure.id}`,
            caption: `${row.structure.name}: ${plural(row.patrons, 'patron', 'patrons')}`,
            segments: [
              { value: Math.min(SPAN, row.patrons), fill: 'fill-warning' },
            ],
          })),
          ...data.welfare.map((row) => ({
            key: `w${row.structure.id}`,
            caption: `${row.structure.name}: ${row.inmates} taken in`,
            segments: [
              { value: Math.min(SPAN, row.inmates), fill: 'fill-success' },
            ],
          })),
        ]}
        max={SPAN}
        noun={['house', 'houses']}
        empty='No tavern or house of welfare stands here.'
      />
      <Listed
        title='Taverns and inns'
        items={data.taverns}
        empty='No tavern stands here.'
        noun={['tavern', 'taverns']}
        itemKey={(item) => item.structure.id}
      >
        {(item) => <TavernCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Houses of welfare'
        items={data.welfare}
        empty='No house of welfare stands here.'
        noun={['house', 'houses']}
        itemKey={(item) => item.structure.id}
      >
        {(item) => <WelfareCard row={item} blocked={blocked} />}
      </Listed>
      {data.commute ? (
        <CommuteCard town={nodeId} row={data.commute} blocked={blocked} />
      ) : (
        <Muted variant='caption'>No way to work is read here.</Muted>
      )}
      {data.cooperative ? (
        <CoopCard faction={nodeId} row={data.cooperative} blocked={blocked} />
      ) : (
        <Muted variant='caption'>It pools no means.</Muted>
      )}
      <ForgeCard
        icon={Home}
        tone='gold'
        title='Keep a house'
        note='Make a building a tavern or a house of welfare.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={Users}
              label='Tend town life now'
              busy={tending.busy}
              onClick={tending.run}
            />
            <Button
              size='sm'
              variant='outline'
              disabled={structureBusy !== null}
              disabledReason={structureBusy ?? undefined}
              onClick={() => tavern.mutate()}
            >
              <Beer />
              Tavern
            </Button>
            <Button
              size='sm'
              disabled={structureBusy !== null}
              disabledReason={structureBusy ?? undefined}
              onClick={() => house.mutate()}
            >
              <HandHeart />
              House of welfare
            </Button>
          </div>
        }
      >
        <NodePicker
          label='Building'
          value={structure}
          onChange={setStructure}
          blocked={blocked}
          types={STRUCTURES}
        />
      </ForgeCard>
      <ForgeCard
        icon={Route}
        tone='info'
        title='Ways and pools'
        note='Read the way to work of a town, or let a faction pool its members means.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              variant='outline'
              disabled={wayBusy !== null}
              disabledReason={wayBusy ?? undefined}
              onClick={() => way.mutate()}
            >
              <Route />
              Way to work
            </Button>
            <Button
              size='sm'
              disabled={poolBusy !== null}
              disabledReason={poolBusy ?? undefined}
              onClick={() => pool.mutate()}
            >
              <Plus />
              Cooperative
            </Button>
          </div>
        }
      >
        <MindPicker
          label='Purpose'
          value={purpose}
          table={table(PURPOSES)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setPurpose}
        />
      </ForgeCard>
    </div>
  )
}
