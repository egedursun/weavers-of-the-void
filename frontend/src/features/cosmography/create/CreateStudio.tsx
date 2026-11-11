import { type ReactNode, useId, useState } from 'react'
import { Check, Layers, Orbit, Sparkles, Workflow } from 'lucide-react'
import { type ActionBody } from '@/api/actions'
import { unitHash } from '@/lib/hash'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Medallion, ShowMore, useShowMore } from '@/components/domain'
import { type KpiTone } from '@/components/domain/KpiTile'
import { Label, Muted, Text } from '@/components/typography'
import { CosmicActionButton } from '@/features/cosmos/CosmicActionButton'
import { useRuleBook } from '@/features/cosmos/model/rules'
import { MindPicker } from '@/features/entity/mind/parts'
import {
  type CosmographyCatalog,
  type KindRecord,
  useCosmographyAction,
} from '../api'
import { armRange, armText, isKindShape, nucleusOdds } from '../galaxyKind'
import { ELEMENTS, NUCLEI } from '../labels'
import { type Ladder, nameTable } from '../ladder'
import { Chip } from '../parts'
import { GalaxyThumb } from '../visual/GalaxyThumb'
import { ClusterThumb, DimensionSigil } from '../visual/ScaleThumbs'
import { type FormInput } from '../visual/galaxyForm'

const EFFECT_LABEL: Record<string, string> = {
  density: 'Star density',
  formation: 'Star formation',
  metallicity: 'Metallicity',
  capacity: 'Travel capacity',
  leak: 'Leak',
  sanity: 'Sanity drain',
  danger: 'Danger',
  heat: 'Medium heat',
  merger: 'Merging',
  veil: 'Veil',
  stability: 'Stability',
  time: 'Time',
  magic: 'Magic',
  hostility: 'Hostility',
}

const PERCENT_EFFECTS = new Set(['density', 'capacity', 'time'])
const TILES_SHOWN = 12
const PREVIEW_ID = 9_000_000

function effectText(key: string, value: number): string {
  return PERCENT_EFFECTS.has(key)
    ? `${EFFECT_LABEL[key] ?? key} ${value}%`
    : `${EFFECT_LABEL[key] ?? key} ${value}`
}

function KindGallery({
  kinds,
  value,
  onPick,
  render,
  noun,
}: {
  kinds: readonly KindRecord[]
  value: string
  onPick: (value: string) => void
  render: (kind: KindRecord) => ReactNode
  noun: [string, string]
}) {
  const page = useShowMore(kinds, TILES_SHOWN)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div
        role='radiogroup'
        aria-label={`Choose a ${noun[0]}`}
        className='grid min-w-0 grid-cols-2 gap-2 @md/studio:grid-cols-4 @4xl/studio:grid-cols-6'
      >
        {page.visible.map((kind) => (
          <Button
            key={kind.value}
            role='radio'
            variant='outline'
            size='card'
            aria-checked={kind.value === value}
            onClick={() => onPick(kind.value)}
            className={cn(
              kind.value === value && 'border-primary bg-primary/10'
            )}
            aria-label={kind.label}
          >
            <span className='relative block min-w-0'>
              {render(kind)}
              {kind.value === value && (
                <span className='absolute top-1 right-1 rounded-full bg-primary p-0.5 text-primary-foreground'>
                  <Check className='size-icon-xs' />
                </span>
              )}
            </span>
            <Text as='span' variant='caption' weight='medium' truncate>
              {kind.label}
            </Text>
          </Button>
        ))}
      </div>
      <ShowMore
        state={page}
        noun={[`kind of ${noun[0]}`, `kinds of ${noun[1]}`]}
      />
    </div>
  )
}

function NameField({
  value,
  onChange,
  disabled,
  placeholder,
}: {
  value: string
  onChange: (value: string) => void
  disabled: boolean
  placeholder: string
}) {
  const id = useId()
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label as='label' htmlFor={id}>
        Name
      </Label>
      <Input
        id={id}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}

function Studio({
  icon,
  tone,
  title,
  note,
  preview,
  chosen,
  gallery,
  fields,
  action,
  id,
}: {
  icon: typeof Orbit
  tone: KpiTone
  title: string
  note: string
  preview: ReactNode
  chosen: KindRecord | undefined
  gallery: ReactNode
  fields: ReactNode
  action: ReactNode
  id?: string
}) {
  return (
    <section
      id={id}
      className='@container/studio flex min-w-0 flex-col gap-4 rounded-xl border bg-card p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={icon} tone={tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text weight='semibold'>{title}</Text>
          <Muted variant='caption'>{note}</Muted>
        </div>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-4 @3xl/studio:grid-cols-5'>
        <div className='flex min-w-0 flex-col gap-3 @3xl/studio:col-span-3'>
          {gallery}
        </div>
        <div className='flex min-w-0 flex-col gap-3 @3xl/studio:col-span-2'>
          {preview}
          {chosen ? (
            <div className='flex min-w-0 flex-col gap-1.5'>
              <Text weight='semibold'>{chosen.label}</Text>
              <Muted variant='caption'>{chosen.description}</Muted>
              <div className='flex min-w-0 flex-wrap gap-1'>
                {Object.entries(chosen.effects ?? {})
                  .filter(([key, value]) => value !== 0 && !isKindShape(key))
                  .map(([key, value]) => (
                    <Chip key={key} icon={Sparkles}>
                      {effectText(key, value)}
                    </Chip>
                  ))}
                {'arms_min' in (chosen.effects ?? {}) && (
                  <>
                    <Chip icon={Sparkles}>
                      {`Arms ${armText(chosen.effects)}`}
                    </Chip>
                    {nucleusOdds(chosen.effects).map(([key, share]) => (
                      <Chip key={key} icon={NUCLEI[key].icon}>
                        {`${NUCLEI[key].label} ${share}%`}
                      </Chip>
                    ))}
                  </>
                )}
              </div>
            </div>
          ) : (
            <Muted variant='caption'>Choose a kind to see what it does.</Muted>
          )}
          {fields}
          {action}
        </div>
      </div>
    </section>
  )
}

function previewGalaxy(kind: KindRecord | undefined, value: string): FormInput {
  const effects = kind?.effects ?? {}
  return {
    id: PREVIEW_ID + Math.round(unitHash(`preview-${value}`) * 1000),
    galaxy_type: (value || 'spiral') as FormInput['galaxy_type'],
    radius: 900,
    arm_count: Math.round(
      armRange(effects).reduce((sum, item) => sum + item) / 2
    ),
    nucleus: nucleusOdds(effects)[0][0],
    star_formation: effects.formation ?? 50,
    metallicity: effects.metallicity ?? 50,
    age_stage: 'mature',
    leak: effects.leak ?? 0,
    merge_progress: 0,
  }
}

export function CreateGalaxyStudio({
  ladder,
  catalog,
  clusterId,
  dimensionId,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog
  clusterId?: number
  dimensionId?: number
}) {
  const [kind, setKind] = useState('')
  const [name, setName] = useState('')
  const [cluster, setCluster] = useState(
    clusterId !== undefined ? String(clusterId) : ''
  )
  const [dimension, setDimension] = useState(
    dimensionId !== undefined ? String(dimensionId) : ''
  )
  const rules = useRuleBook()
  const create = useCosmographyAction(
    'galaxy:create',
    (_: void) => ({
      name: name.trim(),
      galaxy_type: kind as ActionBody<'galaxy:create'>['galaxy_type'],
      cluster_id: cluster ? Number(cluster) : null,
      dimension_id: cluster ? null : dimension ? Number(dimension) : null,
    }),
    'A new galaxy turns in the heavens'
  )
  const busy = create.isPending ? 'The galaxy is forming' : null
  const missing =
    kind === ''
      ? 'Choose its form first'
      : name.trim() === ''
        ? 'Name the galaxy first'
        : null
  const chosen = catalog.galaxy_types.find((row) => row.value === kind)
  return (
    <Studio
      id='create-galaxy'
      icon={Orbit}
      tone='gold'
      title='Set a new galaxy turning'
      note='Choose its form; its arms, star formation and metallicity start from the form and grow with the epochs.'
      chosen={chosen}
      preview={
        <GalaxyThumb
          galaxy={previewGalaxy(chosen, kind)}
          shape={catalog.shape}
          label='Preview of the new galaxy'
          className='aspect-square w-full'
        />
      }
      gallery={
        <KindGallery
          kinds={catalog.galaxy_types}
          value={kind}
          onPick={setKind}
          noun={['galaxy', 'galaxies']}
          render={(row) => (
            <GalaxyThumb
              galaxy={previewGalaxy(row, row.value)}
              shape={catalog.shape}
              label={row.label}
              points={1400}
              className='aspect-square w-full'
            />
          )}
        />
      }
      fields={
        <div className='grid min-w-0 grid-cols-1 gap-2'>
          <NameField
            value={name}
            onChange={setName}
            disabled={busy !== null}
            placeholder='The name it will carry'
          />
          <MindPicker
            label='Cluster'
            value={cluster}
            table={nameTable(ladder.data.clusters)}
            blocked={
              busy ??
              (ladder.data.clusters.length === 0
                ? 'No cluster exists yet; set it loose in a dimension'
                : null)
            }
            onPick={setCluster}
          />
          <MindPicker
            label='Dimension, outside any cluster'
            value={dimension}
            table={nameTable(ladder.data.dimensions)}
            blocked={
              busy ??
              (cluster ? 'It lies in the dimension of its cluster' : null)
            }
            onPick={setDimension}
          />
        </div>
      }
      action={
        <CosmicActionButton
          actionId='galaxy:create'
          label='Set it turning'
          icon={Orbit}
          variant='default'
          cost={rules.get('createGalaxy')}
          pending={create.isPending}
          blockedReason={busy ?? missing ?? undefined}
          onRun={() => {
            create.mutate()
            setName('')
          }}
        />
      }
    />
  )
}

export function CreateClusterStudio({
  ladder,
  catalog,
  dimensionId,
  parentId,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog
  dimensionId?: number
  parentId?: number
}) {
  const [kind, setKind] = useState('')
  const [name, setName] = useState('')
  const [dimension, setDimension] = useState(
    dimensionId !== undefined ? String(dimensionId) : ''
  )
  const [parent, setParent] = useState(
    parentId !== undefined ? String(parentId) : ''
  )
  const rules = useRuleBook()
  const create = useCosmographyAction(
    'cluster:create',
    (_: void) => ({
      name: name.trim(),
      kind: kind as ActionBody<'cluster:create'>['kind'],
      dimension_id: parent ? null : dimension ? Number(dimension) : null,
      parent_cluster_id: parent ? Number(parent) : null,
    }),
    'Galaxies gathered into a new cluster'
  )
  const busy = create.isPending ? 'The cluster is gathering' : null
  const missing =
    kind === ''
      ? 'Choose its kind first'
      : name.trim() === ''
        ? 'Name the cluster first'
        : null
  const chosen = catalog.cluster_kinds.find((row) => row.value === kind)
  return (
    <Studio
      id='create-cluster'
      icon={Workflow}
      tone='verdigris'
      title='Gather a cluster'
      note='A cluster holds galaxies; groups lie inside superclusters, filaments and walls.'
      chosen={chosen}
      preview={
        <ClusterThumb
          cluster={{
            id: PREVIEW_ID,
            kind: (kind || 'galaxy_group') as never,
            galaxies: 4,
            heat: chosen?.effects?.heat ?? 30,
          }}
          label='Preview of the new cluster'
          className='aspect-video w-full'
        />
      }
      gallery={
        <KindGallery
          kinds={catalog.cluster_kinds}
          value={kind}
          onPick={setKind}
          noun={['cluster', 'clusters']}
          render={(row) => (
            <ClusterThumb
              cluster={{
                id: PREVIEW_ID + row.value.length,
                kind: row.value as never,
                galaxies: 4,
                heat: row.effects?.heat ?? 30,
              }}
              label={row.label}
              className='aspect-square w-full'
            />
          )}
        />
      }
      fields={
        <div className='grid min-w-0 grid-cols-1 gap-2'>
          <NameField
            value={name}
            onChange={setName}
            disabled={busy !== null}
            placeholder='The name it will carry'
          />
          <MindPicker
            label='Dimension'
            value={dimension}
            table={nameTable(ladder.data.dimensions)}
            blocked={
              busy ??
              (parent ? 'A cluster inside another lies in its dimension' : null)
            }
            onPick={setDimension}
          />
          <MindPicker
            label='Inside cluster'
            value={parent}
            table={nameTable(ladder.data.clusters)}
            blocked={
              busy ??
              (ladder.data.clusters.length === 0
                ? 'No cluster exists yet to hold it'
                : null)
            }
            onPick={setParent}
          />
        </div>
      }
      action={
        <CosmicActionButton
          actionId='cluster:create'
          label='Gather it'
          icon={Workflow}
          variant='default'
          cost={rules.get('createCluster')}
          pending={create.isPending}
          blockedReason={busy ?? missing ?? undefined}
          onRun={() => {
            create.mutate()
            setName('')
          }}
        />
      }
    />
  )
}

export function CreateDimensionStudio({
  ladder,
  catalog,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog
}) {
  const [kind, setKind] = useState('')
  const [name, setName] = useState('')
  const [parent, setParent] = useState('')
  const [element, setElement] = useState('')
  const rules = useRuleBook()
  const create = useCosmographyAction(
    'dimension:create',
    (_: void) => ({
      name: name.trim(),
      kind: kind as ActionBody<'dimension:create'>['kind'],
      parent_dimension_id: parent ? Number(parent) : null,
      element:
        kind === 'elemental' && element
          ? (element as ActionBody<'dimension:create'>['element'])
          : null,
    }),
    'A new dimension came into being'
  )
  const busy = create.isPending ? 'The dimension is forming' : null
  const missing =
    kind === ''
      ? 'Choose its kind first'
      : name.trim() === ''
        ? 'Name the dimension first'
        : null
  const chosen = catalog.dimension_kinds.find((row) => row.value === kind)
  const sigil = (
    value: string,
    effects: Record<string, number> | undefined,
    id: number
  ) => ({
    id,
    kind: (value || 'prime') as never,
    veil: effects?.veil ?? 50,
    stability: effects?.stability ?? 70,
    magic: effects?.magic ?? 30,
  })
  return (
    <Studio
      id='create-dimension'
      icon={Layers}
      tone='info'
      title='Bring a dimension into being'
      note='A dimension is a whole layer of the one cosmos, with its own time, magic, veil and laws.'
      chosen={chosen}
      preview={
        <DimensionSigil
          dimension={sigil(kind, chosen?.effects, PREVIEW_ID)}
          label='Preview of the new dimension'
          className='aspect-video w-full'
        />
      }
      gallery={
        <KindGallery
          kinds={catalog.dimension_kinds}
          value={kind}
          onPick={setKind}
          noun={['dimension', 'dimensions']}
          render={(row) => (
            <DimensionSigil
              dimension={sigil(
                row.value,
                row.effects,
                PREVIEW_ID + row.value.length
              )}
              label={row.label}
              className='aspect-square w-full'
            />
          )}
        />
      }
      fields={
        <div className='grid min-w-0 grid-cols-1 gap-2'>
          <NameField
            value={name}
            onChange={setName}
            disabled={busy !== null}
            placeholder='The name it will carry'
          />
          <MindPicker
            label='Lies within'
            value={parent}
            table={nameTable(ladder.data.dimensions)}
            blocked={
              busy ??
              (ladder.data.dimensions.length === 0
                ? 'No dimension exists yet to hold it'
                : null)
            }
            onPick={setParent}
          />
          <MindPicker
            label='Element'
            value={element}
            table={ELEMENTS}
            blocked={
              busy ??
              (kind === 'elemental'
                ? null
                : 'Only an elemental plane has an element')
            }
            onPick={setElement}
          />
        </div>
      }
      action={
        <CosmicActionButton
          actionId='dimension:create'
          label='Bring it into being'
          icon={Layers}
          variant='default'
          cost={rules.get('createDimension')}
          pending={create.isPending}
          blockedReason={busy ?? missing ?? undefined}
          onRun={() => {
            create.mutate()
            setName('')
          }}
        />
      }
    />
  )
}
