import { useState } from 'react'
import {
  BadgeCheck,
  Coins,
  FlaskConical,
  Gem,
  Package,
  ShieldAlert,
  Star,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { MANY, SPAN } from '@/features/cycles/model'
import { TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { COMMODITY, WORKSHOP } from '@/features/entity/economy/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { type AgrarianNodeView, useAgrarianAction } from './api'
import { USES } from './labels'
import { HOLDER_TYPES, useAgrarianRow } from './model'

type Keystone = AgrarianNodeView['keystones'][number]
type Brand = AgrarianNodeView['brands'][number]

const NO_WORLD = 'This lies in no world'
const NO_WORKSHOP = 'Every workshop here already has a brand, or there is none'
const LANDS = ['region'] as const
const PRODUCERS = ['species', 'place', 'phenomenon'] as const
const CULTS = ['cult'] as const
const REALMS = ['polity'] as const

function KeystoneCard({
  row,
  blocked,
}: {
  row: Keystone
  blocked: string | null
}) {
  const action = useAgrarianRow(
    'keystone:edit',
    'keystone:delete',
    { keystone_id: row.id },
    blocked
  )
  const use = USES[row.use]
  const commodity = row.commodity
    ? COMMODITY[row.commodity].label
    : 'no common good'
  return (
    <Held
      icon={Gem}
      tone={row.supply < 30 ? 'danger' : 'gold'}
      title={`${row.name}, keystone of ${row.world.name}`}
      caption={`Needed for ${use.label.toLowerCase()} · since epoch ${row.designated_epoch}`}
      removeLabel='Free the world from it'
      editTitle='Set the keystone'
      note='One producer’s yield that an institution needs and a cult holds sacred. Harvesting it thins its producers, whoever controls its source holds a monopoly, those who depend on it suffer when it runs short, the cult turns on a careless controller, and envious realms go to war with the source as their aim. A young world comes to depend on such a yield as soon as one exists.'
      fields={[
        { key: 'name', label: 'Name of the resource', kind: 'text' },
        {
          key: 'producer_entity_id',
          label: 'Producer',
          kind: 'node',
          types: PRODUCERS,
        },
        {
          key: 'source_region_entity_id',
          label: 'Source land',
          kind: 'node',
          types: LANDS,
        },
        {
          key: 'commodity',
          label: 'Traded as',
          kind: 'pick',
          table: table(COMMODITY),
        },
        { key: 'use', label: 'Needed for', kind: 'pick', table: table(USES) },
        {
          key: 'cult_entity_id',
          label: 'Holding cult',
          kind: 'node',
          types: CULTS,
        },
        {
          key: 'controller_entity_id',
          label: 'Controller of the source',
          kind: 'node',
          types: REALMS,
        },
        { key: 'harvest', label: 'Harvest', kind: 'number', min: 0, max: SPAN },
        { key: 'supply', label: 'Supply', kind: 'number', min: 0, max: SPAN },
        { key: 'price', label: 'Price (%)', kind: 'number', min: 0, max: MANY },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Supply'
        value={row.supply}
        tone='legendary'
        icon={Package}
      />
      <Meter
        label='Harvest'
        value={row.harvest}
        tone='warning'
        icon={FlaskConical}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @lg/tiles:grid-cols-2'>
          <KpiTile
            label='Price'
            value={`${row.price}%`}
            icon={Coins}
            tone='gold'
          />
          <KpiTile
            label='Traded as'
            value={commodity}
            icon={Package}
            tone='info'
          />
        </div>
      </div>
      <Facts
        items={[
          [
            'Producer',
            <Ref key='producer' node={row.producer} empty='no producer' />,
          ],
          [
            'Source land',
            <Ref key='source' node={row.source} empty='no source' />,
          ],
          ['Holding cult', <Ref key='cult' node={row.cult} empty='no cult' />],
          [
            'Controller',
            <Ref
              key='controller'
              node={row.controller}
              empty='no realm holds it'
            />,
          ],
          [
            'Made so by',
            <Ref key='by' node={row.designated_by} empty='the world itself' />,
          ],
        ]}
      />
    </Held>
  )
}

function BrandCard({ row, blocked }: { row: Brand; blocked: string | null }) {
  const action = useAgrarianRow(
    'brand:edit',
    'brand:delete',
    { brand_id: row.id },
    blocked
  )
  const shop = WORKSHOP[row.workshop_kind]
  return (
    <Held
      icon={shop.icon}
      tone='gold'
      title={row.name}
      caption={`${shop.label} of ${row.community.name} · since epoch ${row.since_epoch}`}
      removeLabel='Forget the brand'
      editTitle='Set the brand'
      note='Workshops earn a name from the quality of their work and the renowned works of their town. A famous brand raises the price of and the demand for its goods in its town, earns its owner a premium and lifts its town; crime breeds counterfeits that wear the name down. The brand passes with the workshop to its heirs or buyers.'
      fields={[
        { key: 'name', label: 'Name of the brand', kind: 'text' },
        {
          key: 'owner_node_id',
          label: 'Owner',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        {
          key: 'reputation',
          label: 'Reputation',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'quality',
          label: 'Quality of the work',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'renowned',
          label: 'Renowned works of the town',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'counterfeits',
          label: 'Counterfeits',
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
        label='Reputation'
        value={row.reputation}
        tone='legendary'
        icon={Star}
      />
      <Meter
        label='Quality of the work'
        value={row.quality}
        tone='success'
        icon={BadgeCheck}
      />
      <Meter
        label='Counterfeits'
        value={row.counterfeits}
        tone='destructive'
        icon={ShieldAlert}
      />
      <Facts
        items={[
          ['Owner', <Ref key='owner' node={row.owner} empty='no owner' />],
          ['Renowned works of the town', String(row.renowned)],
          ['Workshop', `${shop.label} of ${row.community.name}`],
        ]}
      />
    </Held>
  )
}

function KeystoneForge({
  data,
  blocked,
}: {
  data: AgrarianNodeView
  blocked: string | null
}) {
  const world = data.world
  const gate = world ? blocked : NO_WORLD
  const [name, setName] = useState('')
  const [use, setUse] = useState<keyof typeof USES>('rite')
  const [producer, setProducer] = useState<number | null>(null)
  const [source, setSource] = useState<number | null>(null)
  const [cult, setCult] = useState<number | null>(null)
  const designating = useAgrarianAction(
    'keystone:designate',
    (_: void) => ({
      world_id: world?.id ?? 0,
      name: name.trim(),
      use,
      producer_id: producer,
      source_region_id: source,
      cult_id: cult,
    }),
    'The world depends on it'
  )
  const busy = why(
    world ? (name.trim() === '' ? 'Name the resource' : blocked) : NO_WORLD,
    designating.isPending
  )
  return (
    <ForgeCard
      icon={Gem}
      tone='gold'
      title={world ? `Make a keystone of ${world.name}` : 'Make a keystone'}
      note='Choose the yield the whole world will depend on: who produces it, the land it comes from, the institution that needs it and the cult that holds it sacred. A world has one keystone; setting it again replaces it.'
      columns={3}
      action={
        <Button
          act={designating}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => designating.mutate()}
        >
          <Gem />
          Make it so
        </Button>
      }
    >
      <TextField
        label='Name of the resource'
        value={name}
        blocked={gate}
        onChange={setName}
      />
      <MindPicker
        label='Needed for'
        value={use}
        table={table(USES)}
        blocked={gate}
        onPick={(value) => setUse(value as keyof typeof USES)}
      />
      <NodePicker
        label='Producer'
        value={producer}
        onChange={setProducer}
        blocked={gate}
        types={PRODUCERS}
      />
      <NodePicker
        label='Source land'
        value={source}
        onChange={setSource}
        blocked={gate}
        types={LANDS}
      />
      <NodePicker
        label='Holding cult'
        value={cult}
        onChange={setCult}
        blocked={gate}
        types={CULTS}
      />
    </ForgeCard>
  )
}

function BrandForge({
  data,
  blocked,
}: {
  data: AgrarianNodeView
  blocked: string | null
}) {
  const options = Object.fromEntries(
    data.workshops.map((item) => [
      String(item.id),
      `${WORKSHOP[item.kind].label}, level ${item.level}`,
    ])
  )
  const [workshop, setWorkshop] = useState<string>(
    data.workshops[0] ? String(data.workshops[0].id) : ''
  )
  const [name, setName] = useState('')
  const gate = data.workshops.length > 0 ? blocked : NO_WORKSHOP
  const founding = useAgrarianAction(
    'brand:found',
    (_: void) => ({ workshop_id: Number(workshop), name: name.trim() }),
    'The brand is known'
  )
  const busy = why(
    data.workshops.length > 0
      ? name.trim() === ''
        ? 'Name the brand'
        : workshop === ''
          ? 'Choose a workshop'
          : blocked
      : NO_WORKSHOP,
    founding.isPending
  )
  return (
    <ForgeCard
      icon={Star}
      tone='gold'
      title='Give a workshop a brand'
      note='A workshop of this town becomes known by name; its reputation then follows the quality of its work.'
      columns={2}
      action={
        <Button
          act={founding}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => founding.mutate()}
        >
          <Star />
          Name it
        </Button>
      }
    >
      <MindPicker
        label='Workshop'
        value={workshop}
        table={options}
        blocked={gate}
        onPick={setWorkshop}
      />
      <TextField
        label='Name of the brand'
        value={name}
        blocked={gate}
        onChange={setName}
      />
    </ForgeCard>
  )
}

export function StaplesPanel({
  data,
  blocked,
}: {
  data: AgrarianNodeView
  blocked: string | null
}) {
  return (
    <div data-surface='StaplesPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Keystone of the world'
        items={data.keystones}
        empty='No resource here is what a world depends on.'
        noun={['keystone', 'keystones']}
        itemKey={(item) => item.id}
      >
        {(item) => <KeystoneCard row={item} blocked={blocked} />}
      </Listed>
      <KeystoneForge data={data} blocked={blocked} />
      <Listed
        title='Brands'
        items={data.brands}
        empty='No workshop here is known by name.'
        noun={['brand', 'brands']}
        itemKey={(item) => item.workshop_id}
      >
        {(item) => <BrandCard row={item} blocked={blocked} />}
      </Listed>
      <BrandForge data={data} blocked={blocked} />
    </div>
  )
}
