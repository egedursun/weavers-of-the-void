import { useState } from 'react'
import { Leaf, Plus, Sprout } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type NatureNodeView, useNatureAction } from './api'
import { DEFENCES, FERMENTS } from './labels'
import { HOLDER_TYPES, MANY, SPAN, useNatureRow } from './model'

type View = NatureNodeView
type Culture = View['cultures'][number]
type Soil = NonNullable<View['soil']>

function SoilCard({
  soil,
  regionId,
  blocked,
}: {
  soil: Soil
  regionId: number
  blocked: string | null
}) {
  const action = useNatureRow(
    'soil_microbiota:edit',
    'soil_microbiota:delete',
    { region_id: regionId },
    blocked
  )
  return (
    <Held
      icon={Leaf}
      tone={soil.sterile_epochs > 0 ? 'warning' : 'success'}
      title='The life of the soil'
      caption={`Life ${soil.life} of ${SPAN} · nutrients recycle at ${soil.recycling_pct}% · sterile for ${soil.sterile_epochs} epochs · read in epoch ${soil.updated_epoch}`}
      removeLabel='Leave the soil to itself'
      editTitle='Set the life of the soil'
      note='Moisture and fertility feed the life of a soil, pollution and salt kill it, and a sterile soil heals only slowly. A living soil recycles its nutrients faster.'
      fields={[
        { key: 'life', label: 'Life', kind: 'number', min: 0, max: SPAN },
        {
          key: 'sterile_epochs',
          label: 'Epochs sterile',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={soil.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Life (${soil.life} of ${SPAN})`}
        value={soil.life}
        tone={soil.sterile_epochs > 0 ? 'warning' : 'success'}
        icon={Leaf}
      />
    </Held>
  )
}

function CultureCard({
  row,
  blocked,
}: {
  row: Culture
  blocked: string | null
}) {
  const action = useNatureRow(
    'ferment_culture:edit',
    'ferment_culture:delete',
    { record_id: row.id },
    blocked
  )
  const ferment = FERMENTS[row.kind]
  return (
    <Held
      icon={ferment.icon}
      tone={row.lost_epoch !== null ? 'muted' : ferment.tone}
      title={`${ferment.label} of ${row.holder.name}`}
      caption={`Quality ${row.quality} · kept since epoch ${row.since_epoch}${row.lost_epoch !== null ? ` · lost in epoch ${row.lost_epoch}` : ''}`}
      removeLabel='Lose the culture'
      editTitle='Set the culture'
      note='A kept culture grows better with use and makes the baked, cured, fermented, pickled and brewed dishes of its town more pleasing. Sickness where it is kept may kill it, and it passes along trade routes to partner towns.'
      fields={[
        {
          key: 'holder_entity_id',
          label: 'Kept by',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        { key: 'kind', label: 'Culture', kind: 'pick', table: table(FERMENTS) },
        { key: 'quality', label: 'Quality', kind: 'number', min: 0, max: SPAN },
        {
          key: 'lost_epoch',
          label: 'Lost in epoch',
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
          ['Kept by', <Ref key='holder' node={row.holder} empty='no one' />],
        ]}
      />
      <Meter
        label={`Quality (${row.quality} of ${SPAN})`}
        value={row.quality}
        tone='success'
        icon={ferment.icon}
      />
    </Held>
  )
}

export function SoilPanel({
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
  const region = kind === 'region'
  const keeper = (HOLDER_TYPES as readonly string[]).includes(kind ?? '')
  const [life, setLife] = useState('50')
  const [holder, setHolder] = useState<number | null>(keeper ? nodeId : null)
  const [ferment, setFerment] = useState('yeast')
  const [quality, setQuality] = useState('30')
  const seeding = useNatureAction(
    'soil_microbiota:set',
    (_: void) => ({
      region_id: nodeId,
      life: Math.max(0, Math.min(SPAN, Number(life) || 0)),
      sterile_epochs: 0,
    }),
    'The life of the soil is set'
  )
  const keeping = useNatureAction(
    'ferment_culture:create',
    (_: void) => ({
      holder_entity_id: holder ?? 0,
      kind: ferment as Culture['kind'],
      quality: Math.max(0, Math.min(SPAN, Number(quality) || 0)),
    }),
    'The culture is kept'
  )
  const seedBusy = why(
    blocked ??
      (!region
        ? 'Only a land has a soil'
        : data.soil
          ? 'The soil has its life already; set it above'
          : null),
    seeding.isPending
  )
  const keepBusy = why(
    blocked ?? (holder === null ? 'Choose who keeps the culture' : null),
    keeping.isPending
  )
  return (
    <div data-surface='SoilPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-soil-life'
        title='The life of the soil'
        legend={[{ text: 'Life', variant: 'success' }]}
        rows={
          data.soil
            ? [
                {
                  key: 'soil',
                  caption: `Life ${data.soil.life}, recycling at ${data.soil.recycling_pct}%`,
                  segments: [{ value: data.soil.life, fill: 'fill-success' }],
                },
              ]
            : []
        }
        max={SPAN}
        noun={['soil', 'soils']}
        empty='Only a land has a soil; this has none read yet.'
      />
      {data.soil && (
        <ul className='flex min-w-0 flex-col gap-3'>
          <SoilCard soil={data.soil} regionId={nodeId} blocked={blocked} />
        </ul>
      )}
      <Bars
        chart='chart-plant-defences'
        title='How far defended plants cover the land'
        legend={[{ text: 'Cover', variant: 'warning' }]}
        rows={data.defences.map((row) => ({
          key: row.defence,
          caption: `${DEFENCES[row.defence].label}: ${row.cover_pct}%`,
          segments: [{ value: row.cover_pct, fill: 'fill-warning' }],
        }))}
        max={SPAN}
        noun={['defence', 'defences']}
        empty='No defended plant covers this land.'
      />
      <Bars
        chart='chart-cultures'
        title='Ferment cultures and their quality'
        legend={[{ text: 'Quality', variant: 'success' }]}
        rows={data.cultures.map((row) => ({
          key: String(row.id),
          caption: `${FERMENTS[row.kind].label} of ${row.holder.name}: quality ${row.quality}`,
          segments: [{ value: row.quality, fill: 'fill-success' }],
        }))}
        max={SPAN}
        noun={['culture', 'cultures']}
        empty='No ferment culture is kept here.'
      />
      <Listed
        title='Ferment cultures'
        items={data.cultures}
        empty='No ferment culture is kept here.'
        noun={['culture', 'cultures']}
        itemKey={(item) => item.id}
      >
        {(item) => <CultureCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Sprout}
        tone='success'
        title='Set the life of the soil'
        note='Give a land a living soil before the living nature step reads it.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={seedBusy !== null}
            disabledReason={seedBusy ?? undefined}
            onClick={() => seeding.mutate()}
          >
            <Plus />
            Set it
          </Button>
        }
      >
        <NumberField
          label='Life'
          value={life}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setLife}
        />
      </ForgeCard>
      <ForgeCard
        icon={Leaf}
        tone='gold'
        title='Give a ferment culture'
        note='A town, association, house or hall keeps a culture that improves its dishes.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={keepBusy !== null}
            disabledReason={keepBusy ?? undefined}
            onClick={() => keeping.mutate()}
          >
            <Plus />
            Give it
          </Button>
        }
      >
        <NodePicker
          label='Kept by'
          value={holder}
          onChange={setHolder}
          blocked={blocked}
          types={HOLDER_TYPES}
        />
        <MindPicker
          label='Culture'
          value={ferment}
          table={table(FERMENTS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setFerment}
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
