import { useState } from 'react'
import { Bug, Clover, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type FolkwaysNodeView, useFolkwaysAction } from './api'
import {
  ATTRIBUTIONS,
  CHARM_POWERS,
  LUCK_REACHES,
  LUCK_SIGNS,
  MISHAP_KINDS,
  RESPONSES,
} from './labels'
import {
  ITEM_TYPES,
  MORTAL_TYPES,
  SPAN,
  TOWN_TYPES,
  useFolkwaysRow,
  withNone,
} from './model'

type Mishap = FolkwaysNodeView['mishaps'][number]
type Belief = FolkwaysNodeView['beliefs'][number]
type Charm = FolkwaysNodeView['charms'][number]

const NO_PEOPLE = 'Only a people, or one of its folk, holds beliefs about luck'

function MishapCard({ row, blocked }: { row: Mishap; blocked: string | null }) {
  const action = useFolkwaysRow(
    'mishap:edit',
    'mishap:delete',
    { mishap_id: row.id },
    blocked
  )
  const kind = MISHAP_KINDS[row.kind]
  const blamed = row.attribution ? ATTRIBUTIONS[row.attribution] : null
  const answer = row.response ? RESPONSES[row.response] : null
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={`${kind.label} in ${row.town.name}`}
      caption={`Epoch ${row.epoch} · ${row.explained ? 'its folk can explain it' : 'its folk cannot explain it'}${blamed ? ` · blamed on ${blamed.label.toLowerCase()}` : ''}`}
      removeLabel='Strike the misfortune'
      editTitle='Set the misfortune'
      note='A misfortune keeps its true cause beside what its folk blame. A people blames by its values and its beliefs about luck, unless its medicine or farming lets it explain the cause; what it blames sets how it answers: a rite, an offering, a charm, a purification, an accusation, a safety custom or nothing.'
      fields={[
        {
          key: 'kind',
          label: 'Misfortune',
          kind: 'pick',
          table: table(MISHAP_KINDS),
        },
        { key: 'true_cause', label: 'True cause', kind: 'text' },
        { key: 'explained', label: 'Explained', kind: 'pick', table: YES_NO },
        {
          key: 'attribution',
          label: 'Blamed on',
          kind: 'pick',
          table: withNone(table(ATTRIBUTIONS), 'Not yet blamed'),
        },
        {
          key: 'response',
          label: 'Answered by',
          kind: 'pick',
          table: withNone(table(RESPONSES), 'Not yet answered'),
        },
        {
          key: 'victim_node_id',
          label: 'Fell on',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'cause_node_id',
          label: 'Truly caused by',
          kind: 'node',
          types: [],
          kinds: ['entity', 'son', 'foreign_god'],
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={answer ? <Tag item={answer} /> : undefined}
    >
      <Facts
        items={[
          ['True cause', row.true_cause],
          [
            'Fell on',
            <Ref key='victim' node={row.victim} empty='the town as a whole' />,
          ],
          [
            'Truly caused by',
            <Ref key='cause' node={row.cause} empty='no one' />,
          ],
        ]}
      />
    </Held>
  )
}

function BeliefCard({ row, blocked }: { row: Belief; blocked: string | null }) {
  const action = useFolkwaysRow(
    'luck_belief:edit',
    'luck_belief:delete',
    { belief_id: row.id },
    blocked
  )
  const sign = LUCK_SIGNS[row.sign]
  const reach = LUCK_REACHES[row.reach]
  return (
    <Held
      icon={sign.icon}
      tone={row.lucky ? 'success' : 'warning'}
      title={row.name}
      caption={`${row.lucky ? 'Lucky' : 'Unlucky'} · ${sign.label.toLowerCase()} · touches ${reach.label.toLowerCase()}`}
      removeLabel='Strike the belief'
      editTitle='Set the belief'
      note='A belief about luck makes its people read misfortunes it touches as omens or fate and answer them with rites; a belief that touches battle steadies or shakes their armies.'
      fields={[
        { key: 'name', label: 'Belief', kind: 'text' },
        { key: 'sign', label: 'Sign', kind: 'pick', table: table(LUCK_SIGNS) },
        {
          key: 'reach',
          label: 'Touches',
          kind: 'pick',
          table: table(LUCK_REACHES),
        },
        { key: 'lucky', label: 'Lucky', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={reach} />}
    />
  )
}

function CharmCard({ row, blocked }: { row: Charm; blocked: string | null }) {
  const action = useFolkwaysRow(
    'charm:edit',
    'charm:delete',
    { item_id: row.item.id },
    blocked
  )
  const power = CHARM_POWERS[row.power]
  return (
    <Held
      icon={power.icon}
      tone={row.real ? 'gold' : 'muted'}
      title={`${row.item.name}, a charm of ${power.label.toLowerCase()}`}
      caption={
        row.real ? 'Its power is real' : 'Believed in; its power is not real'
      }
      removeLabel='Undo the charm'
      editTitle='Set the charm'
      note='A charm calms its bearer whether or not its power is real. Its power is real where it is enchanted, blessed or holds a spirit: then it wards off misfortune, makes its bearer fruitful or mends them.'
      fields={[
        {
          key: 'power',
          label: 'Power',
          kind: 'pick',
          table: table(CHARM_POWERS),
        },
        { key: 'real', label: 'Real', kind: 'pick', table: YES_NO },
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={power} />}
    >
      <Meter
        label={`Strength (${row.strength} of ${SPAN})`}
        value={row.strength}
        tone='success'
        icon={Clover}
      />
    </Held>
  )
}

export function MishapPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: FolkwaysNodeView
  blocked: string | null
}) {
  const people = data.people?.id ?? null
  const [town, setTown] = useState<number | null>(
    kind === 'settlement' ? nodeId : null
  )
  const [victim, setVictim] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [mishap, setMishap] = useState('bad_luck')
  const [sign, setSign] = useState('day')
  const [reach, setReach] = useState('harvest')
  const [belief, setBelief] = useState('')
  const [item, setItem] = useState<number | null>(
    kind === 'item' ? nodeId : null
  )
  const [power, setPower] = useState('protection')
  const sending = useFolkwaysAction(
    'mishap:create',
    (_: void) => ({
      town_id: town ?? 0,
      kind: mishap as Mishap['kind'],
      victim_id: victim,
      cause_id: null,
    }),
    'A misfortune befalls the town'
  )
  const believing = useFolkwaysAction(
    'luck_belief:create',
    (_: void) => ({
      people_id: people ?? 0,
      sign: sign as Belief['sign'],
      reach: reach as Belief['reach'],
      lucky: true,
      name: belief.trim(),
    }),
    'The people believe it'
  )
  const charming = useFolkwaysAction(
    'charm:set',
    (_: void) => ({
      item_id: item ?? 0,
      power: power as Charm['power'],
      strength: 50,
    }),
    'The item is a charm'
  )
  const sendBusy = why(
    blocked ?? (town === null ? 'Choose a town' : null),
    sending.isPending
  )
  const beliefBusy = why(
    blocked ??
      (people === null ? NO_PEOPLE : !belief.trim() ? 'Name the belief' : null),
    believing.isPending
  )
  const charmBusy = why(
    blocked ?? (item === null ? 'Choose an item' : null),
    charming.isPending
  )
  return (
    <div data-surface='MishapPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-mishaps'
        title='Misfortunes and what was blamed'
        legend={[
          { text: 'Explained', variant: 'success' },
          { text: 'Unexplained', variant: 'warning' },
        ]}
        rows={data.mishaps.map((row) => ({
          key: row.id,
          caption: `${MISHAP_KINDS[row.kind].label}, epoch ${row.epoch}: ${row.attribution ? ATTRIBUTIONS[row.attribution].label : 'not yet blamed'}`,
          segments: [
            {
              value: SPAN,
              fill: row.explained ? 'fill-success' : 'fill-warning',
            },
          ],
        }))}
        max={SPAN}
        noun={['misfortune', 'misfortunes']}
        empty='No misfortune touches this.'
      />
      <Listed
        title='Misfortunes'
        items={data.mishaps}
        empty='No misfortune touches this.'
        noun={['misfortune', 'misfortunes']}
        itemKey={(entry) => entry.id}
      >
        {(entry) => <MishapCard row={entry} blocked={blocked} />}
      </Listed>
      <Listed
        title='Beliefs about luck'
        items={data.beliefs}
        empty='Its people holds no beliefs about luck.'
        noun={['belief', 'beliefs']}
        itemKey={(entry) => entry.id}
      >
        {(entry) => <BeliefCard row={entry} blocked={blocked} />}
      </Listed>
      <Listed
        title='Charms'
        items={data.charms}
        empty='It holds no charm.'
        noun={['charm', 'charms']}
        itemKey={(entry) => entry.item.id}
      >
        {(entry) => <CharmCard row={entry} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Bug}
        tone='danger'
        title='Send a misfortune'
        note='Its folk read it by their own values and beliefs and answer it their own way.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={sendBusy !== null}
            disabledReason={sendBusy ?? undefined}
            onClick={() => sending.mutate()}
          >
            <Bug />
            Send it
          </Button>
        }
      >
        <NodePicker
          label='Town'
          value={town}
          onChange={setTown}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <MindPicker
          label='Misfortune'
          value={mishap}
          table={table(MISHAP_KINDS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setMishap}
        />
        <NodePicker
          label='Falls on'
          value={victim}
          onChange={setVictim}
          blocked={blocked}
          types={MORTAL_TYPES}
        />
      </ForgeCard>
      <ForgeCard
        icon={Clover}
        tone='success'
        title='Give its people a belief about luck'
        note='Name it as the people would; it is lucky, and you may turn it unlucky above.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={beliefBusy !== null}
            disabledReason={beliefBusy ?? undefined}
            onClick={() => believing.mutate()}
          >
            <Plus />
            Let them believe it
          </Button>
        }
      >
        <TextField
          label='Belief'
          value={belief}
          blocked={blocked}
          onChange={setBelief}
        />
        <MindPicker
          label='Sign'
          value={sign}
          table={table(LUCK_SIGNS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setSign}
        />
        <MindPicker
          label='Touches'
          value={reach}
          table={table(LUCK_REACHES)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setReach}
        />
      </ForgeCard>
      <ForgeCard
        icon={Clover}
        tone='gold'
        title='Make an item a charm'
        note='Its power is real if the item is enchanted, blessed or holds a spirit.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={charmBusy !== null}
            disabledReason={charmBusy ?? undefined}
            onClick={() => charming.mutate()}
          >
            <Clover />
            Make the charm
          </Button>
        }
      >
        <NodePicker
          label='Item'
          value={item}
          onChange={setItem}
          blocked={blocked}
          types={ITEM_TYPES}
        />
        <MindPicker
          label='Power'
          value={power}
          table={table(CHARM_POWERS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setPower}
        />
      </ForgeCard>
    </div>
  )
}
