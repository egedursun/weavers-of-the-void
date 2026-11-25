import { useState } from 'react'
import { FlaskConical, Fish, Plus, Wrench } from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
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
import { type CraftsNodeView, useCraftsAction } from './api'
import { CATCH_RIGHTS, GEAR, GROUNDS, PRODUCTS } from './labels'
import { MANY, SPAN, useCraftsRow, useCraftsStep } from './model'

type View = CraftsNodeView
type Ground = View['grounds'][number]
type Works = View['works'][number]

const SOURCES = ['resource', 'species'] as const
const LANDS = ['region'] as const
const OWNERS = ['polity', 'settlement', 'people'] as const

function GroundCard({ row, blocked }: { row: Ground; blocked: string | null }) {
  const action = useCraftsRow(
    'catch_ground:edit',
    'catch_ground:delete',
    { source_id: row.source.id, region_id: row.region.id },
    blocked
  )
  const ground = GROUNDS[row.ground]
  return (
    <Held
      icon={ground.icon}
      tone={row.collapsed ? 'danger' : ground.tone}
      title={`${ground.label}: ${row.source.name}`}
      caption={`${GEAR[row.gear].label} · effort ${row.effort} · last catch ${row.last_catch} · first stock ${row.first_stock} · stock ${row.stock}${row.collapsed ? ' · collapsed' : ''}`}
      removeLabel='Strike the ground'
      editTitle='Set the ground'
      note='Gear and effort set the catch; worked below its collapse mark, a share of its first stock, a ground gives out and regrows slowly until it recovers. Others who work owned waters sour the owner, and sea beasts wound their hunters.'
      fields={[
        { key: 'ground', label: 'Ground', kind: 'pick', table: table(GROUNDS) },
        { key: 'gear', label: 'Gear', kind: 'pick', table: table(GEAR) },
        {
          key: 'right',
          label: 'Right to work it',
          kind: 'pick',
          table: table(CATCH_RIGHTS),
        },
        { key: 'owner_node_id', label: 'Owner', kind: 'node', types: OWNERS },
        { key: 'effort', label: 'Effort', kind: 'number', min: 0, max: SPAN },
        {
          key: 'collapse_at',
          label: 'Collapses below (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'collapsed', label: 'Collapsed', kind: 'pick', table: YES_NO },
        {
          key: 'first_stock',
          label: 'First stock',
          kind: 'number',
          min: 1,
          max: MANY,
        },
        {
          key: 'stock',
          label: 'Stock left (worked shores, beds and ponds)',
          kind: 'number',
          min: 0,
          max: 100,
        },
        {
          key: 'last_catch',
          label: 'Last catch',
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
      <Facts
        items={[
          ['Land', <Ref key='land' node={row.region} empty='no land' />],
          ['Right', CATCH_RIGHTS[row.right].label],
          ['Owner', <Ref key='owner' node={row.owner} empty='no owner' />],
        ]}
      />
      <Meter
        label={`Effort (${row.effort} of ${SPAN}); collapses below ${row.collapse_at}%`}
        value={row.effort}
        tone={row.collapsed ? 'destructive' : 'info'}
        icon={Fish}
      />
    </Held>
  )
}

function WorksCard({ row, blocked }: { row: Works; blocked: string | null }) {
  const action = useCraftsRow(
    'chemical_works:edit',
    'chemical_works:delete',
    { settlement_id: row.settlement.id, product: row.product },
    blocked
  )
  const product = PRODUCTS[row.product]
  return (
    <Held
      icon={product.icon}
      tone={product.tone}
      title={`Works for ${product.label.toLowerCase()}`}
      caption={`Output ${row.output} · hazard ${row.hazard} · pollution ${row.pollution} · ${plural(row.accidents, 'accident', 'accidents')} · set up in epoch ${row.founded_epoch}`}
      removeLabel='Pull the works down'
      editTitle='Set the works'
      note='The works turn raw goods into their product; soap eases disease, fertiliser feeds the fields, explosives open the mines. Their hazard brings accidents and their pollution fouls water and soil.'
      fields={[
        { key: 'output', label: 'Output', kind: 'number', min: 0, max: SPAN },
        { key: 'hazard', label: 'Hazard', kind: 'number', min: 0, max: SPAN },
        {
          key: 'pollution',
          label: 'Pollution',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'accidents',
          label: 'Accidents',
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
      <Facts
        items={[
          ['Town', <Ref key='town' node={row.settlement} empty='no town' />],
        ]}
      />
      <Meter
        label={`Output (${row.output} of ${SPAN})`}
        value={row.output}
        tone='success'
        icon={FlaskConical}
      />
    </Held>
  )
}

export function TradesPanel({
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
  const town = kind === 'settlement'
  const [source, setSource] = useState<number | null>(null)
  const [land, setLand] = useState<number | null>(data.region?.id ?? null)
  const [ground, setGround] = useState('fishery')
  const [gear, setGear] = useState('nets')
  const [product, setProduct] = useState('dye')
  const reading = useCraftsAction(
    'catch_ground:set',
    (_: void) => ({
      source_id: source ?? 0,
      region_id: land ?? 0,
      ground: ground as Ground['ground'],
      gear: gear as Ground['gear'],
    }),
    'The ground is read'
  )
  const founding = useCraftsAction(
    'chemical_works:set',
    (_: void) => ({
      settlement_id: nodeId,
      product: product as Works['product'],
    }),
    'The works are set up'
  )
  const working = useCraftsStep(
    'trades:run',
    {},
    blocked,
    'The trades are worked'
  )
  const groundBusy = why(
    blocked ??
      (source === null
        ? 'Choose a fishing ground or a hunted kind'
        : land === null
          ? 'Choose the land'
          : null),
    reading.isPending
  )
  const worksBusy = why(
    blocked ??
      (!town
        ? 'Only a town sets up chemical works'
        : data.works.some((row) => row.product === product)
          ? 'It has works for that already; adjust them above'
          : null),
    founding.isPending
  )
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <div data-surface='GroundsPanel' className='flex min-w-0 flex-col gap-4'>
        <Bars
          chart='chart-grounds'
          title='Grounds and their effort'
          legend={[
            { text: 'Worked', variant: 'success' },
            { text: 'Collapsed', variant: 'destructive' },
          ]}
          rows={data.grounds.map((row) => ({
            key: `${row.source.id}-${row.region.id}`,
            caption: `${row.source.name}: effort ${row.effort}, last catch ${row.last_catch}`,
            segments: [
              {
                value: Math.min(SPAN, row.effort),
                fill: row.collapsed ? 'fill-destructive' : 'fill-success',
              },
            ],
          }))}
          max={SPAN}
          noun={['ground', 'grounds']}
          empty='No fishing or hunting ground touches this.'
        />
        <Listed
          title='Fishing and hunting grounds'
          items={data.grounds}
          empty='No fishing or hunting ground touches this.'
          noun={['ground', 'grounds']}
          itemKey={(item) => `${item.source.id}-${item.region.id}`}
        >
          {(item) => <GroundCard row={item} blocked={blocked} />}
        </Listed>
        <ForgeCard
          icon={Fish}
          tone='info'
          title='Read a ground'
          note='A fishing ground of a resource, or the range of a wild kind trapped or fowled in a land.'
          columns={2}
          action={
            <div className='flex min-w-0 flex-wrap gap-2'>
              <StepButton
                icon={Wrench}
                label='Work the trades now'
                busy={working.busy}
                onClick={working.run}
              />
              <Button
                act={reading}
                size='sm'
                disabled={groundBusy !== null}
                disabledReason={groundBusy ?? undefined}
                onClick={() => reading.mutate()}
              >
                <Plus />
                Read it
              </Button>
            </div>
          }
        >
          <NodePicker
            label='Fishing ground or hunted kind'
            value={source}
            onChange={setSource}
            blocked={blocked}
            types={SOURCES}
          />
          <NodePicker
            label='Land'
            value={land}
            onChange={setLand}
            blocked={blocked}
            types={LANDS}
          />
          <MindPicker
            label='Ground'
            value={ground}
            table={table(GROUNDS)}
            placeholder='Choose'
            blocked={blocked}
            onPick={setGround}
          />
          <MindPicker
            label='Gear'
            value={gear}
            table={table(GEAR)}
            placeholder='Choose'
            blocked={blocked}
            onPick={setGear}
          />
        </ForgeCard>
      </div>
      <div data-surface='WorksPanel' className='flex min-w-0 flex-col gap-4'>
        <Bars
          chart='chart-chemistry'
          title='Output of the chemical works'
          legend={[
            { text: 'Output', variant: 'success' },
            { text: 'Pollution', variant: 'warning' },
          ]}
          rows={data.works.map((row) => ({
            key: row.product,
            caption: `${PRODUCTS[row.product].label}: output ${row.output}, pollution ${row.pollution}`,
            segments: [
              { value: Math.min(SPAN, row.output), fill: 'fill-success' },
              { value: Math.min(SPAN, row.pollution), fill: 'fill-warning' },
            ],
          }))}
          max={SPAN * 2}
          noun={['works', 'works']}
          empty='No chemical works stand here.'
        />
        <Listed
          title='Chemical works'
          items={data.works}
          empty='No chemical works stand here.'
          noun={['works', 'works']}
          itemKey={(item) => item.product}
        >
          {(item) => <WorksCard row={item} blocked={blocked} />}
        </Listed>
        <ForgeCard
          icon={FlaskConical}
          tone='verdigris'
          title='Set up works'
          note='Works for a product of the chemist, made from the raw goods of the town.'
          columns={2}
          action={
            <Button
              act={founding}
              size='sm'
              disabled={worksBusy !== null}
              disabledReason={worksBusy ?? undefined}
              onClick={() => founding.mutate()}
            >
              <Plus />
              Set them up
            </Button>
          }
        >
          <MindPicker
            label='Product'
            value={product}
            table={table(PRODUCTS)}
            placeholder='Choose'
            blocked={blocked}
            onPick={setProduct}
          />
        </ForgeCard>
      </div>
    </div>
  )
}
