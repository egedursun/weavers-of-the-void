import { useState } from 'react'
import { CloudFog, Shield, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, EntityLink, PagedList, Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import {
  type Cosmography,
  type CosmographyCatalog,
  type PhenomenonRecord,
  catalogLabel,
  catalogTable,
  useCosmography,
  useCosmographyAction,
} from './api'
import { PHENOMENON_CAUSES } from './labels'
import { Chip, Meter, RecordEditor, RecordPick, RecordRow } from './parts'

export function PhenomenonCard({
  phenomenon,
  catalog,
}: {
  phenomenon: PhenomenonRecord
  catalog: CosmographyCatalog | undefined
}) {
  const edit = useCosmographyAction<{
    values: Record<string, unknown>
    release: string[]
  }>('phenomenon:edit', (vars) => ({
    phenomenon_id: phenomenon.entity_id,
    ...vars,
  }))
  const contain = useCosmographyAction<void>(
    'phenomenon:contain',
    () => ({ phenomenon_id: phenomenon.entity_id, amount: 40 }),
    'Your ward holds it back'
  )
  const spread = useCosmographyAction<{
    region_id: number
    intensity: number | null
  }>('phenomenon:footprint', (vars) => ({
    phenomenon_id: phenomenon.entity_id,
    ...vars,
  }))
  const [region, setRegion] = useState<number | null>(null)
  const [strength, setStrength] = useState('40')
  const busy =
    edit.isPending || contain.isPending || spread.isPending ? 'Working' : null
  return (
    <RecordRow
      icon={CloudFog}
      tone={phenomenon.intensity >= 70 ? 'danger' : 'info'}
      title={
        <EntityLink kind='entity' id={String(phenomenon.entity_id)}>
          {phenomenon.name}
        </EntityLink>
      }
      caption={`${catalogLabel(catalog?.phenomenon_kinds, phenomenon.kind)} · from ${PHENOMENON_CAUSES[phenomenon.cause].toLowerCase()} · epoch ${phenomenon.formed_epoch}`}
      aside={
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => contain.mutate()}
        >
          <Shield />
          Ward it
        </Button>
      }
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <Meter
          label='Intensity'
          value={phenomenon.intensity}
          tone='destructive'
        />
        <Meter
          label='Containment'
          value={phenomenon.containment}
          tone='success'
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        {(phenomenon.footprints ?? []).map((print) => (
          <Button
            key={print.region_entity_id}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() =>
              spread.mutate({
                region_id: print.region_entity_id,
                intensity: null,
              })
            }
          >
            {`Region #${print.region_entity_id} · ${print.intensity}%`}
          </Button>
        ))}
        {(phenomenon.footprints ?? []).length === 0 && (
          <Muted variant='caption'>It covers no region.</Muted>
        )}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 rounded-lg border border-dashed p-2 sm:grid-cols-3'>
        <RecordPick
          label='Region'
          types={['region']}
          value={region}
          onChange={setRegion}
          worldId={phenomenon.world_id ?? undefined}
        />
        <NumberField
          label='Strength there'
          value={strength}
          min={0}
          max={100}
          disabled={busy !== null}
          onChange={setStrength}
        />
        <Button
          size='sm'
          disabled={busy !== null || region === null}
          disabledReason={
            busy ?? (region === null ? 'Choose a region first' : undefined)
          }
          onClick={() =>
            region !== null &&
            spread.mutate({
              region_id: region,
              intensity: Number(strength) || 0,
            })
          }
        >
          <Sparkles />
          Spread it there
        </Button>
      </div>
      <RecordEditor
        title='Reshape this phenomenon'
        note='Intensity, growth and containment you set are held. Tap a region above to draw it back from there.'
        fields={[
          {
            key: 'intensity',
            label: 'Intensity',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'growth',
            label: 'Growth per epoch',
            kind: 'number',
            min: -100,
            max: 100,
          },
          {
            key: 'containment',
            label: 'Containment',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'kind',
            label: 'Kind',
            kind: 'pick',
            table: catalogTable(catalog?.phenomenon_kinds),
          },
        ]}
        locked={phenomenon.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function RaiseForm({
  data,
  catalog,
}: {
  data: Cosmography
  catalog: CosmographyCatalog | undefined
}) {
  const [kind, setKind] = useState('')
  const [region, setRegion] = useState<number | null>(null)
  const [intensity, setIntensity] = useState('50')
  const raise = useCosmographyAction<void>(
    'phenomenon:create',
    () => ({ kind, region_id: region, intensity: Number(intensity) || 50 }),
    'A phenomenon took hold'
  )
  const busy = raise.isPending ? 'It is forming' : null
  const missing =
    kind === '' || region === null ? 'Choose a kind and a region first' : null
  return (
    <div className='grid min-w-0 grid-cols-1 gap-2 rounded-lg border border-dashed p-3 md:grid-cols-3'>
      <MindPicker
        label='Kind'
        value={kind}
        table={catalogTable(catalog?.phenomenon_kinds)}
        blocked={busy}
        onPick={setKind}
      />
      <RecordPick
        label='Region'
        types={['region']}
        value={region}
        onChange={setRegion}
      />
      <NumberField
        label='Intensity'
        value={intensity}
        min={0}
        max={100}
        disabled={busy !== null}
        onChange={setIntensity}
      />
      <Button
        size='sm'
        disabled={busy !== null || missing !== null}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() => raise.mutate()}
      >
        <CloudFog />
        Raise it
      </Button>
      <Chip>{`${data.phenomena.length} stand now`}</Chip>
    </div>
  )
}

export function PhenomenaPanel({
  data,
  catalog,
}: {
  data: Cosmography
  catalog: CosmographyCatalog | undefined
}) {
  return (
    <Section
      id='section-phenomenon'
      title='Phenomena'
      description='Lasting changes over regions: they grow, spread, fade against their wards and change the land they hold.'
      icon={CloudFog}
      tone='info'
    >
      <div
        data-surface='PhenomenonSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {data.phenomena.length === 0 ? (
          <EmptyState
            icon={CloudFog}
            size='compact'
            title='No phenomenon holds a land'
            description='Raise one below, or let rites, rifts and battles leave them.'
          />
        ) : (
          <PagedList
            items={data.phenomena}
            initial={5}
            noun={['phenomenon', 'phenomena']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(row) => row.entity_id}
          >
            {(row) => <PhenomenonCard phenomenon={row} catalog={catalog} />}
          </PagedList>
        )}
        <RaiseForm data={data} catalog={catalog} />
      </div>
    </Section>
  )
}

export function PhenomenonSection({
  entityId,
  catalog,
}: {
  entityId: number
  catalog?: CosmographyCatalog
}) {
  const view = useCosmography()
  if (!view.data) return null
  const found = view.data.phenomena.find((row) => row.entity_id === entityId)
  return (
    <Section
      id='section-phenomenon'
      title='As a phenomenon'
      icon={CloudFog}
      tone='info'
    >
      {found ? (
        <ul className='flex min-w-0 flex-col gap-2'>
          <PhenomenonCard phenomenon={found} catalog={catalog} />
        </ul>
      ) : (
        <EmptyState
          icon={CloudFog}
          size='compact'
          title='No profile yet'
          description='Its profile forms at the next epoch.'
        />
      )}
    </Section>
  )
}
