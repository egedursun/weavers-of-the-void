import { useState } from 'react'
import { Eye, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { table } from '@/features/arcana/labels'
import {
  Chip,
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import { type FossilBedView, useEndsAction, useNodeFossils } from './api'
import { FOSSIL_ICON, FOSSIL_READINGS, FOSSIL_SOURCES } from './labels'

const BEDS_SHOWN = 6
const YES_NO = { true: 'Yes', false: 'No' }

const FIELDS: readonly Field[] = [
  {
    key: 'source',
    label: 'Remains of',
    kind: 'pick',
    table: table(FOSSIL_SOURCES),
  },
  { key: 'richness', label: 'Richness', kind: 'number', min: 1, max: 100 },
  {
    key: 'frozen',
    label: 'Kept in ice',
    kind: 'pick',
    table: YES_NO,
  },
  {
    key: 'reading',
    label: 'Read as',
    kind: 'pick',
    table: table(FOSSIL_READINGS),
  },
]

function Bed({ bed, blocked }: { bed: FossilBedView; blocked: string | null }) {
  const source = FOSSIL_SOURCES[bed.source]
  const reading = FOSSIL_READINGS[bed.reading]
  const editing = useEndsAction(
    'fossil_bed:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({ bed_id: bed.id, ...vars }),
    'The fossil bed keeps its new values'
  )
  const revealing = useEndsAction(
    'fossil_bed:reveal',
    (_: void) => ({ bed_id: bed.id }),
    'The remains come to light'
  )
  const removing = useEndsAction(
    'fossil_bed:delete',
    (_: void) => ({ bed_id: bed.id }),
    'The fossil bed is gone'
  )
  const found = bed.found_epoch !== null
  return (
    <RecordRow
      icon={source.icon}
      tone={source.tone}
      title={source.label}
      caption={
        found
          ? `Found in epoch ${bed.found_epoch}, read as ${reading.label.toLowerCase()}`
          : `Laid down in epoch ${bed.laid_epoch}, still hidden`
      }
      aside={<Chip icon={reading.icon}>Richness {bed.richness}</Chip>}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Ref node={bed.source_node} empty='no single source' />
        {bed.finder && <Ref node={bed.finder} empty='no finder' />}
        {bed.frozen && (
          <Chip icon={FOSSIL_ICON} variant='warning'>
            Kept in ice
            {bed.disease ? `, holding ${bed.disease.name}` : ''}
          </Chip>
        )}
      </div>
      <RecordEditor
        title='Set this bed'
        note='Values you set are held against the engine until you release them.'
        fields={FIELDS}
        locked={bed.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={Eye}
          label='Bring it to light now'
          busy={why(
            blocked ?? (found ? 'It has already been found' : null),
            revealing.isPending
          )}
          onClick={() => revealing.mutate()}
        />
        <StepButton
          icon={Trash2}
          label='Remove this bed'
          busy={why(blocked, removing.isPending)}
          onClick={() => removing.mutate()}
        />
      </div>
    </RecordRow>
  )
}

export function FossilSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeFossils(nodeId)
  const data = query.data
  const regionId = data?.region?.id ?? null
  const absent = data?.absent_reason ?? null
  const blocked = readOnlyReason ?? absent
  const page = useShowMore(data?.beds ?? [], BEDS_SHOWN, BEDS_SHOWN * 2)
  const [source, setSource] =
    useState<keyof typeof FOSSIL_SOURCES>('extinct_species')
  const [richness, setRichness] = useState('30')
  const placing = useEndsAction(
    'fossil_bed:create',
    (_: void) => ({
      region_id: regionId ?? 0,
      source,
      richness: Number(richness) || 1,
    }),
    'Remains lie hidden in that land now'
  )
  const running = useEndsAction(
    'fossils:run',
    (_: void) => ({}),
    'Every fossil bed is read'
  )
  const placeBlocked =
    blocked ?? (regionId === null ? 'This thing stands in no land' : null)
  return (
    <Section
      id='section-fossils'
      title='Fossils: remains of what died out in its land'
      description='Beds of the remains of kinds, beasts and peoples that died out, and of previous creations, in the land this thing stands in: when they were found, by whom, and how those who found them read them. Things in no land show the beds of their world; the Creator and stars hold none.'
      icon={FOSSIL_ICON}
      tone='muted'
    >
      <div data-surface='FossilSection' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading the remains under its land' />
        ) : query.isError ? (
          <EmptyState
            icon={FOSSIL_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
              <KpiTile
                label='Land'
                value={query.data.region?.name ?? 'none'}
                icon={FOSSIL_ICON}
                tone='muted'
              />
              <KpiTile
                label='Found on its world'
                value={String(query.data.world_found)}
                icon={Eye}
                tone='gold'
              />
              <KpiTile
                label='Still hidden on its world'
                value={String(query.data.world_hidden)}
                icon={FOSSIL_ICON}
                tone='info'
              />
            </div>
            <Bars
              chart='chart-fossils'
              title='Richness of the beds of this land'
              legend={[
                { text: 'Found', variant: 'warning' },
                { text: 'Hidden', variant: 'outline' },
              ]}
              rows={page.visible.map((bed) => ({
                key: String(bed.id),
                caption: `${FOSSIL_SOURCES[bed.source].label}: richness ${bed.richness}${bed.found_epoch === null ? ', hidden' : ''}`,
                segments: [
                  {
                    value: bed.richness,
                    fill:
                      bed.found_epoch === null ? 'fill-muted' : 'fill-warning',
                  },
                ],
              }))}
              max={100}
              noun={['bed', 'beds']}
              empty='No remains lie in this land.'
            />
            {query.data.beds.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {page.visible.map((bed) => (
                    <Bed key={bed.id} bed={bed} blocked={readOnlyReason} />
                  ))}
                </ul>
                <ShowMore state={page} />
              </div>
            ) : (
              <EmptyState
                icon={FOSSIL_ICON}
                size='inline'
                title='No remains lie here'
                description={
                  absent ??
                  'Nothing that died out has left its remains in this land yet.'
                }
              />
            )}
            <ForgeCard
              icon={FOSSIL_ICON}
              tone='muted'
              title='Lay down remains in this land'
              note='They stay hidden until digging, upheaval or your hand brings them to light.'
              columns={2}
              action={
                <Button
                  size='sm'
                  disabled={why(placeBlocked, placing.isPending) !== null}
                  disabledReason={
                    why(placeBlocked, placing.isPending) ?? undefined
                  }
                  onClick={() => placing.mutate()}
                >
                  <FOSSIL_ICON />
                  Lay them down
                </Button>
              }
            >
              <ChoiceField
                label='Remains of'
                value={source}
                table={FOSSIL_SOURCES}
                blocked={placeBlocked}
                onPick={(next) =>
                  setSource(next as keyof typeof FOSSIL_SOURCES)
                }
              />
              <NumberField
                label='Richness'
                value={richness}
                min={1}
                max={100}
                onChange={setRichness}
              />
            </ForgeCard>
            <StepButton
              icon={FOSSIL_ICON}
              label='Read every fossil bed now'
              busy={why(readOnlyReason, running.isPending)}
              onClick={() => running.mutate()}
            />
          </>
        )}
      </div>
    </Section>
  )
}
