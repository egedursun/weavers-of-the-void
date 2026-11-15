import { useState } from 'react'
import {
  BrickWall,
  Droplets,
  Lock,
  Package,
  Plus,
  ScrollText,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { MATERIAL } from '@/features/entity/wilds/labels'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type MeansNodeView, useMeansAction } from './api'
import { AIDS, CONTAINERS, LIFTS, LOCKS, MEDIA, PORT_ICON } from './labels'
import { MANY, SPAN, useMeansRow } from './model'

type View = MeansNodeView
const YES_NO = { true: 'Yes', false: 'No' }
const LOCK_CHOICES = { none: 'No lock', ...table(LOCKS) }
const VAULT_TYPES = ['structure', 'settlement'] as const
const WORK_TYPES = ['item', 'artwork'] as const

function clamp(text: string, high: number): number {
  return Math.max(0, Math.min(high, Number(text) || 0))
}

export function WritingPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const people = data.people
  const custom = data.custom
  const [medium, setMedium] = useState('clay_tablet')
  const [work, setWork] = useState<number | null>(null)
  const [workMedium, setWorkMedium] = useState('paper')
  const customRow = useMeansRow(
    'writing_custom:edit',
    'writing_custom:delete',
    { people_id: people?.id ?? 0 },
    blocked
  )
  const setting = useMeansAction(
    'writing_custom:set',
    (_: void) => ({
      people_id: people?.id ?? 0,
      medium: medium as View['works'][number]['medium'],
    }),
    'The people write on it now'
  )
  const recording = useMeansAction(
    'written_work:set',
    (_: void) => ({
      work_id: work ?? 0,
      medium: workMedium as View['works'][number]['medium'],
      condition: SPAN,
      copies: 1,
    }),
    'The work is set down on it'
  )
  const setBusy = why(
    blocked ??
      (people === null
        ? 'This thing belongs to no people whose writing it shares'
        : null),
    setting.isPending
  )
  const recordBusy = why(
    blocked ?? (work === null ? 'Choose a written work first' : null),
    recording.isPending
  )
  return (
    <div data-surface='WritingPanel' className='flex min-w-0 flex-col gap-4'>
      <Facts
        items={[
          ['Writing of', <Ref key='people' node={people} empty='no people' />],
          ['Written on', custom ? MEDIA[custom.medium].label : 'Not yet read'],
          ['Since epoch', custom ? String(custom.since_epoch) : 'Never'],
        ]}
      />
      {custom && (
        <Held
          icon={MEDIA[custom.medium].icon}
          tone={MEDIA[custom.medium].tone}
          title={`${custom.people.name} write on ${MEDIA[custom.medium].label.toLowerCase()}`}
          caption={`Since epoch ${custom.since_epoch}`}
          removeLabel='Strike the custom'
          editTitle='Set the medium'
          note='The medium decides how works rot in the damp, burn or bake in fire, and how fast they are copied.'
          fields={[
            {
              key: 'medium',
              label: 'Medium',
              kind: 'pick',
              table: table(MEDIA),
            },
          ]}
          locked={custom.locked}
          blocked={customRow.busy}
          onEdit={customRow.onEdit}
          onRemove={customRow.onRemove}
        />
      )}
      <Bars
        chart='chart-writing'
        title='How whole each written work is'
        legend={[{ text: 'Condition', variant: 'success' }]}
        rows={data.works.map((row) => ({
          key: String(row.work.id),
          caption: `${row.work.name}: ${row.condition} on ${MEDIA[row.medium].label.toLowerCase()}, ${row.copies} ${row.copies === 1 ? 'copy' : 'copies'}`,
          segments: [{ value: row.condition, fill: 'fill-success' }],
        }))}
        max={SPAN}
        noun={['work', 'works']}
        empty='No written work is kept here yet.'
      />
      <Listed
        title='Written works'
        items={data.works}
        empty='No written work is kept here yet.'
        noun={['work', 'works']}
        itemKey={(item) => item.work.id}
      >
        {(item) => <WorkCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={ScrollText}
        tone='gold'
        title='Set what this people writes on'
        note={`${people ? people.name : 'The people'} take up this medium for what they write from now on.`}
        columns={2}
        action={
          <Button
            size='sm'
            disabled={setBusy !== null}
            disabledReason={setBusy ?? undefined}
            onClick={() => setting.mutate()}
          >
            <Plus />
            Set it
          </Button>
        }
      >
        <MindPicker
          label='Medium'
          value={medium}
          table={table(MEDIA)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setMedium}
        />
      </ForgeCard>
      <ForgeCard
        icon={ScrollText}
        tone='info'
        title='Set down a written work'
        note='A book or record takes this medium, whole and in one copy.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={recordBusy !== null}
            disabledReason={recordBusy ?? undefined}
            onClick={() => recording.mutate()}
          >
            <Plus />
            Set it down
          </Button>
        }
      >
        <NodePicker
          label='Written work'
          value={work}
          onChange={setWork}
          blocked={blocked}
          types={WORK_TYPES}
        />
        <MindPicker
          label='Medium'
          value={workMedium}
          table={table(MEDIA)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setWorkMedium}
        />
      </ForgeCard>
    </div>
  )
}

function WorkCard({
  row,
  blocked,
}: {
  row: View['works'][number]
  blocked: string | null
}) {
  const action = useMeansRow(
    'written_work:edit',
    'written_work:delete',
    { work_id: row.work.id },
    blocked
  )
  const medium = MEDIA[row.medium]
  return (
    <Held
      icon={medium.icon}
      tone={medium.tone}
      title={<Ref node={row.work} />}
      caption={`${medium.label}, written in epoch ${row.written_epoch}`}
      removeLabel='Forget its medium'
      editTitle='Set the work'
      note='A worn work teaches less; every copy spares it some decay.'
      fields={[
        { key: 'medium', label: 'Medium', kind: 'pick', table: table(MEDIA) },
        {
          key: 'condition',
          label: 'Condition',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'copies', label: 'Copies', kind: 'number', min: 0, max: MANY },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Condition (${row.condition} of ${SPAN})`}
        value={row.condition}
        tone='success'
        icon={medium.icon}
      />
    </Held>
  )
}

export function VaultsPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const [holder, setHolder] = useState<number | null>(data.node.id)
  const [lock, setLock] = useState('warded')
  const [quality, setQuality] = useState('40')
  const securing = useMeansAction(
    'security:set',
    (_: void) => ({
      holder_id: holder ?? 0,
      lock:
        lock === 'none'
          ? null
          : (lock as NonNullable<View['vaults'][number]['lock']>),
      lock_quality: clamp(quality, SPAN),
      sealed: false,
      guards: 0,
      traps: false,
    }),
    'The vault is secured'
  )
  const busy = why(
    blocked ?? (holder === null ? 'Choose a store or town first' : null),
    securing.isPending
  )
  return (
    <div data-surface='VaultsPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-vaults'
        title='How well each store is locked'
        legend={[{ text: 'Lock quality', variant: 'success' }]}
        rows={data.vaults.map((row) => ({
          key: String(row.holder.id),
          caption: `${row.holder.name}: ${row.lock_quality}, ${row.thwarted} ${row.thwarted === 1 ? 'theft' : 'thefts'} thwarted`,
          segments: [{ value: row.lock_quality, fill: 'fill-success' }],
        }))}
        max={SPAN}
        noun={['vault', 'vaults']}
        empty='No store here is locked yet; metalworking towns lock their stores.'
      />
      <Listed
        title='Vaults'
        items={data.vaults}
        empty='No store here is locked yet.'
        noun={['vault', 'vaults']}
        itemKey={(item) => item.holder.id}
      >
        {(item) => <VaultCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Lock}
        tone='info'
        title='Secure a vault'
        note='A store, treasury or town is locked; thieves contend against its lock, seal, guards and traps.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => securing.mutate()}
          >
            <Plus />
            Secure it
          </Button>
        }
      >
        <NodePicker
          label='Store or town'
          value={holder}
          onChange={setHolder}
          blocked={blocked}
          types={VAULT_TYPES}
        />
        <MindPicker
          label='Lock'
          value={lock}
          table={LOCK_CHOICES}
          placeholder='Choose'
          blocked={blocked}
          onPick={setLock}
        />
        <NumberField
          label='Lock quality'
          value={quality}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setQuality}
        />
      </ForgeCard>
    </div>
  )
}

function VaultCard({
  row,
  blocked,
}: {
  row: View['vaults'][number]
  blocked: string | null
}) {
  const action = useMeansRow(
    'security:edit',
    'security:delete',
    { holder_id: row.holder.id },
    blocked
  )
  const lock = row.lock
    ? LOCKS[row.lock]
    : { label: 'No lock', icon: Lock, tone: 'muted' as const }
  return (
    <Held
      icon={lock.icon}
      tone={lock.tone}
      title={<Ref node={row.holder} />}
      caption={`${lock.label}${row.sealed ? ', sealed' : ''}${row.traps ? ', trapped' : ''}, ${row.guards} ${row.guards === 1 ? 'guard' : 'guards'} since epoch ${row.since_epoch}`}
      removeLabel='Lay it open'
      editTitle='Set the vault'
      note='A master smith of the town improves its lock; a seal names a thief; a trap harms one.'
      fields={[
        { key: 'lock', label: 'Lock', kind: 'pick', table: LOCK_CHOICES },
        {
          key: 'lock_quality',
          label: 'Lock quality',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'sealed', label: 'Sealed', kind: 'pick', table: YES_NO },
        { key: 'guards', label: 'Guards', kind: 'number', min: 0, max: MANY },
        { key: 'traps', label: 'Trapped', kind: 'pick', table: YES_NO },
        {
          key: 'thwarted',
          label: 'Thefts thwarted',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Lock quality (${row.lock_quality} of ${SPAN})`}
        value={row.lock_quality}
        tone='info'
        icon={lock.icon}
      />
    </Held>
  )
}

export function WaterPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const town = data.town
  const [device, setDevice] = useState('shaduf')
  const [count, setCount] = useState('1')
  const raising = useMeansAction(
    'water_lift:set',
    (_: void) => ({
      settlement_id: town?.id ?? 0,
      device: device as View['lifts'][number]['device'],
      count: clamp(count, MANY),
    }),
    'The devices lift water'
  )
  const busy = why(
    blocked ??
      (town === null ? 'This thing lies in no town to lift water for' : null),
    raising.isPending
  )
  return (
    <div data-surface='WaterPanel' className='flex min-w-0 flex-col gap-4'>
      <Facts
        items={[['Town', <Ref key='town' node={town} empty='no town' />]]}
      />
      <Bars
        chart='chart-water'
        title='How much water each kind of device lifts'
        legend={[{ text: 'Capacity', variant: 'secondary' }]}
        rows={data.lifts.map((row) => ({
          key: row.device,
          caption: `${LIFTS[row.device].label}: ${row.count} lifting ${row.capacity}`,
          segments: [{ value: row.capacity, fill: 'fill-info' }],
        }))}
        max={Math.max(1, ...data.lifts.map((row) => row.capacity))}
        noun={['device', 'devices']}
        empty='No water is lifted here; dry towns and deep mines raise the devices they know.'
      />
      <Listed
        title='Water-lifting devices'
        items={data.lifts}
        empty='No water is lifted here.'
        noun={['kind', 'kinds']}
        itemKey={(item) => item.device}
      >
        {(item) => (
          <LiftCard row={item} townId={town?.id ?? 0} blocked={blocked} />
        )}
      </Listed>
      <ForgeCard
        icon={Droplets}
        tone='info'
        title='Raise water-lifting devices'
        note='Devices water the fields of a dry land, drain deep mines and clean the town.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => raising.mutate()}
          >
            <Plus />
            Raise them
          </Button>
        }
      >
        <MindPicker
          label='Device'
          value={device}
          table={table(LIFTS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setDevice}
        />
        <NumberField
          label='How many'
          value={count}
          min={0}
          max={MANY}
          disabled={blocked !== null}
          onChange={setCount}
        />
      </ForgeCard>
    </div>
  )
}

function LiftCard({
  row,
  townId,
  blocked,
}: {
  row: View['lifts'][number]
  townId: number
  blocked: string | null
}) {
  const action = useMeansRow(
    'water_lift:edit',
    'water_lift:delete',
    { settlement_id: townId, device: row.device },
    blocked
  )
  const lift = LIFTS[row.device]
  return (
    <Held
      icon={lift.icon}
      tone={lift.tone}
      title={`${row.count} ${lift.label.toLowerCase()}`}
      caption={`Lifting ${row.capacity} since epoch ${row.since_epoch}`}
      removeLabel='Take them down'
      editTitle='Set the devices'
      note='Screws, chain and steam pumps drain mines; every device waters the fields of a dry land.'
      fields={[
        { key: 'count', label: 'How many', kind: 'number', min: 0, max: MANY },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

export function PilotsPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const town = data.town
  const [aid, setAid] = useState('compass')
  const [quality, setQuality] = useState('30')
  const taking = useMeansAction(
    'navigation_kit:set',
    (_: void) => ({
      holder_id: town?.id ?? 0,
      aid: aid as View['kits'][number]['aid'],
      quality: clamp(quality, SPAN),
    }),
    'The pilots take up the instrument'
  )
  const busy = why(
    blocked ??
      (town === null
        ? 'This thing lies in no port whose pilots could take it up'
        : null),
    taking.isPending
  )
  return (
    <div data-surface='PilotsPanel' className='flex min-w-0 flex-col gap-4'>
      <Meter
        label={`Accuracy of the instruments (${data.accuracy} of ${SPAN})`}
        value={data.accuracy}
        tone='info'
        icon={PORT_ICON}
      />
      <Bars
        chart='chart-pilots'
        title='How true each instrument is'
        legend={[{ text: 'Quality', variant: 'secondary' }]}
        rows={data.kits.map((row) => ({
          key: row.aid,
          caption: `${AIDS[row.aid].label}: ${row.quality}${row.works ? '' : ', useless in this world'}`,
          segments: [
            {
              value: row.quality,
              fill: row.works ? 'fill-info' : 'fill-muted',
            },
          ],
        }))}
        max={SPAN}
        noun={['instrument', 'instruments']}
        empty='The pilots here use no instrument; ports take up those they know.'
      />
      <Listed
        title='Instruments'
        items={data.kits}
        empty='The pilots here use no instrument.'
        noun={['instrument', 'instruments']}
        itemKey={(item) => item.aid}
      >
        {(item) => (
          <KitCard row={item} townId={town?.id ?? 0} blocked={blocked} />
        )}
      </Listed>
      <ForgeCard
        icon={PORT_ICON}
        tone='info'
        title='Give the port an instrument'
        note='A compass points true only where the world is magnetic enough; accuracy spares sea roads and opens the open sea.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => taking.mutate()}
          >
            <Plus />
            Give it
          </Button>
        }
      >
        <MindPicker
          label='Instrument'
          value={aid}
          table={table(AIDS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setAid}
        />
        <NumberField
          label='Quality'
          value={quality}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setQuality}
        />
      </ForgeCard>
    </div>
  )
}

function KitCard({
  row,
  townId,
  blocked,
}: {
  row: View['kits'][number]
  townId: number
  blocked: string | null
}) {
  const action = useMeansRow(
    'navigation_kit:edit',
    'navigation_kit:delete',
    { holder_id: townId, aid: row.aid },
    blocked
  )
  const aid = AIDS[row.aid]
  return (
    <Held
      icon={aid.icon}
      tone={row.works ? aid.tone : 'muted'}
      title={aid.label}
      caption={`${row.works ? 'Points true' : 'Useless in this world'}, since epoch ${row.since_epoch}`}
      removeLabel='Take it away'
      editTitle='Set the instrument'
      note='Skilled navigators of the port refine their instruments each epoch.'
      fields={[
        { key: 'quality', label: 'Quality', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Quality (${row.quality} of ${SPAN})`}
        value={row.quality}
        tone='info'
        icon={aid.icon}
      />
    </Held>
  )
}

export function ContainersPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const town = data.town
  const [kind, setKind] = useState('amphora')
  const [count, setCount] = useState('20')
  const stocking = useMeansAction(
    'container_stock:set',
    (_: void) => ({
      community_id: town?.id ?? 0,
      kind: kind as View['containers'][number]['kind'],
      count: clamp(count, MANY),
      broken: 0,
    }),
    'The containers are stocked'
  )
  const busy = why(
    blocked ??
      (town === null
        ? 'This thing lies in no town that keeps containers'
        : null),
    stocking.isPending
  )
  return (
    <div data-surface='ContainersPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-containers'
        title='How much each kind of container carries'
        legend={[{ text: 'Capacity', variant: 'warning' }]}
        rows={data.containers.map((row) => ({
          key: row.kind,
          caption: `${CONTAINERS[row.kind].label}: ${row.count} carrying ${row.capacity}${row.sealed ? ', sealed' : ''}`,
          segments: [{ value: row.capacity, fill: 'fill-gold' }],
        }))}
        max={Math.max(1, ...data.containers.map((row) => row.capacity))}
        noun={['kind', 'kinds']}
        empty='No containers are kept here; potters, coopers and weavers make them.'
      />
      <Listed
        title='Containers'
        items={data.containers}
        empty='No containers are kept here.'
        noun={['kind', 'kinds']}
        itemKey={(item) => item.kind}
      >
        {(item) => (
          <StockCard row={item} townId={town?.id ?? 0} blocked={blocked} />
        )}
      </Listed>
      <ForgeCard
        icon={Package}
        tone='gold'
        title='Stock containers'
        note='Containers carry a town’s trade and sealed ones keep its stores from spoiling.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => stocking.mutate()}
          >
            <Plus />
            Stock them
          </Button>
        }
      >
        <MindPicker
          label='Container'
          value={kind}
          table={table(CONTAINERS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setKind}
        />
        <NumberField
          label='How many'
          value={count}
          min={0}
          max={MANY}
          disabled={blocked !== null}
          onChange={setCount}
        />
      </ForgeCard>
    </div>
  )
}

function StockCard({
  row,
  townId,
  blocked,
}: {
  row: View['containers'][number]
  townId: number
  blocked: string | null
}) {
  const action = useMeansRow(
    'container_stock:edit',
    'container_stock:delete',
    { community_id: townId, kind: row.kind },
    blocked
  )
  const kind = CONTAINERS[row.kind]
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={`${row.count} ${kind.label.toLowerCase()}`}
      caption={`Carrying ${row.capacity}; ${row.broken} broken so far${row.sealed ? '; sealed against spoiling' : ''}`}
      removeLabel='Empty the stock'
      editTitle='Set the stock'
      note='Broken containers leave stamped marks that diggers later read.'
      fields={[
        { key: 'count', label: 'Whole', kind: 'number', min: 0, max: MANY },
        { key: 'broken', label: 'Broken', kind: 'number', min: 0, max: MANY },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

export function BuildingPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const building = data.building
  const [material, setMaterial] = useState('fired_brick')
  const setting = useMeansAction(
    'node_material:set',
    (_: void) => ({
      node_id: data.node.id,
      material: material as NonNullable<
        NonNullable<View['building']>['material']
      >,
    }),
    'The work is built of it now'
  )
  const busy = why(
    blocked ??
      (building === null ? 'Only a structure is built of a material' : null),
    setting.isPending
  )
  return (
    <div data-surface='BuildingPanel' className='flex min-w-0 flex-col gap-4'>
      <Facts
        items={[
          [
            'Built of',
            building?.material
              ? MATERIAL[building.material]
              : 'Not a structure, or of no known material',
          ],
          [
            'Resists water',
            building
              ? `${building.water_resistance} of ${SPAN}`
              : 'Not a structure',
          ],
          [
            'Technique needed',
            building?.needs ? building.needs.replace(/_/g, ' ') : 'None',
          ],
          [
            'Can be repaired',
            building
              ? building.can_repair
                ? 'Yes'
                : 'No, its makers forgot how'
              : 'Not a structure',
          ],
          [
            'Weathering',
            building
              ? `${building.weathering_pct}% of the decay of its material`
              : 'Not a structure',
          ],
        ]}
      />
      <Bars
        chart='chart-building'
        title='How its material stands'
        legend={[{ text: 'Of a hundred', variant: 'secondary' }]}
        rows={
          building
            ? [
                {
                  key: 'water',
                  caption: `Resists water: ${building.water_resistance}`,
                  segments: [
                    { value: building.water_resistance, fill: 'fill-info' },
                  ],
                },
                {
                  key: 'weather',
                  caption: `Weathers at ${building.weathering_pct}%`,
                  segments: [
                    {
                      value: Math.min(SPAN * 2, building.weathering_pct) / 2,
                      fill: 'fill-warning',
                    },
                  ],
                },
              ]
            : []
        }
        max={SPAN}
        noun={['trait', 'traits']}
        empty='Only a structure is built of a material.'
      />
      {building && (
        <Meter
          label={`Resists water (${building.water_resistance} of ${SPAN})`}
          value={building.water_resistance}
          tone='info'
          icon={BrickWall}
        />
      )}
      <ForgeCard
        icon={BrickWall}
        tone='warning'
        title='Build it of another material'
        note='The material decides how the work weathers in the damp, burns in fire and turns sieges, and whether its town can repair it.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => setting.mutate()}
          >
            <Plus />
            Build it so
          </Button>
        }
      >
        <MindPicker
          label='Material'
          value={material}
          table={MATERIAL}
          placeholder='Choose'
          blocked={blocked}
          onPick={setMaterial}
        />
      </ForgeCard>
    </div>
  )
}
