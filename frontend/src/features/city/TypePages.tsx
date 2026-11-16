import { Suspense, lazy, useState, type ReactNode } from 'react'
import { Hammer, Home, Users } from 'lucide-react'
import { postAction } from '@/api/actions'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PageHeader,
  PagedList,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { Chip, Facts, ForgeCard, RecordRow } from '@/features/cosmography/parts'
import { hasWebGL2 } from '@/features/cosmos/useCosmosViewSettings'
import { why } from '@/features/dominion/model'
import { humanize } from '@/features/entity/actions/schema'
import { COMMODITY } from '@/features/entity/economy/labels'
import { EntityChoice } from '@/features/entity/economy/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { CLASS_SPEC } from '@/features/entity/society/labels'
import { KIND_SPEC } from '@/features/entity/society/structureLabels'
import { Ref } from '@/features/gatherings/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { HOUSING, SERVICES } from '@/features/urban/labels'
import { type StructureType, useStructureTypes } from './api'
import { CIVIC, STATES, ZONES } from './labels'
import { HOUSING_LOOK, type Look, STRUCTURE_LOOK } from './models'
import { DWELLING_ICON, type TypeSelection } from './typeKeys'

const TypePreview3D = lazy(() => import('./TypePreview3D'))
const TOWN_TYPES = ['settlement'] as const

export function Preview({
  look,
  label,
  icon: Icon,
}: {
  look: Look
  label: string
  icon: typeof Home
}) {
  const still: ReactNode = (
    <div
      role='img'
      aria-label={label}
      className='flex size-full items-center justify-center text-primary'
    >
      <Icon className='size-icon-xl' />
    </div>
  )
  return (
    <div className='relative min-w-0 overflow-hidden rounded-md border surface-well border-gild/45 bg-muted/70'>
      <div className='aspect-video w-full'>
        {hasWebGL2() ? (
          <Suspense fallback={still}>
            <TypePreview3D look={look} label={label} fallback={still} />
          </Suspense>
        ) : (
          still
        )}
      </div>
    </div>
  )
}

function CommissionForge({
  row,
  worldId,
}: {
  row: StructureType
  worldId: number
}) {
  const [town, setTown] = useState<string | null>(null)
  const [level, setLevel] = useState('1')
  const commission = useGodAction({
    run: () =>
      postAction('structure:commission', {
        site_id: Number(town),
        kind: row.kind,
        level: Math.max(1, Math.min(5, Number(level) || 1)),
        funds: 0,
      }),
    success: `A ${row.label.toLowerCase()} is begun`,
  })
  const busy =
    why(null, commission.isPending) ??
    (town === null ? 'Choose the town first' : null)
  return (
    <ForgeCard
      icon={Hammer}
      tone='gold'
      title={`Build a ${row.label.toLowerCase()}`}
      note='Set one more of this type in any town; the planner places it in its zone, and the town’s builders raise it.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => commission.mutate()}
        >
          <Hammer />
          Begin the work
        </Button>
      }
    >
      <EntityChoice
        label='Town'
        types={TOWN_TYPES}
        worldId={worldId}
        value={town}
        blocked={null}
        placeholder='Choose a town'
        onChange={setTown}
      />
      <NumberField
        label='Level (1–5)'
        min={1}
        max={5}
        value={level}
        blocked={null}
        onChange={setLevel}
      />
    </ForgeCard>
  )
}

function BuildingType({
  row,
  worldId,
}: {
  row: StructureType
  worldId: number
}) {
  const spec = KIND_SPEC[row.kind]
  const zone = ZONES[row.zone]
  const count = (state: StructureType['instances'][number]['state']) =>
    row.instances.filter((item) => item.state === state).length
  return (
    <div className='@container/type flex min-w-0 flex-col gap-4'>
      <PageHeader
        eyebrow='Building type'
        title={row.label}
        description={`Stands in the ${zone.label.toLowerCase()} zone${row.service ? ` and serves ${SERVICES[row.service].label.toLowerCase()}` : ''}; ${row.instances.length} built in this world. Every one of them is listed below, and each is ruled from its own record.`}
        icon={spec.icon}
      />
      <Preview
        look={STRUCTURE_LOOK[row.kind]}
        label={`The look of a ${row.label.toLowerCase()}`}
        icon={spec.icon}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Chip icon={zone.icon}>{`${zone.label} zone`}</Chip>
        {row.civic && (
          <Chip icon={CIVIC[row.civic].icon}>{CIVIC[row.civic].label}</Chip>
        )}
        {row.service && (
          <Chip
            icon={SERVICES[row.service].icon}
          >{`Serves ${SERVICES[row.service].label.toLowerCase()}`}</Chip>
        )}
        {row.amenity && <Chip variant='secondary'>Raises desirability</Chip>}
        {row.nuisance && <Chip variant='secondary'>Lowers desirability</Chip>}
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 @xl/type:grid-cols-4'>
        <KpiTile
          label='Standing'
          value={count('complete')}
          icon={spec.icon}
          tone='success'
        />
        <KpiTile
          label='Being built'
          value={count('building') + count('planned')}
          icon={Hammer}
          tone='warning'
        />
        <KpiTile
          label='Damaged'
          value={count('damaged')}
          icon={spec.icon}
          tone='danger'
        />
        <KpiTile
          label='In ruins'
          value={count('ruined')}
          icon={spec.icon}
          tone='muted'
        />
      </div>
      <Facts
        items={[
          ['Group', row.group ? humanize(row.group) : 'none'],
          ['Staffed by', row.staff ? CLASS_SPEC[row.staff].label : 'nobody'],
          ['Smallest town', row.tier ? humanize(row.tier) : 'any'],
          ['Upkeep', row.upkeep ? COMMODITY[row.upkeep].label : 'none'],
        ]}
      />
      <CommissionForge row={row} worldId={worldId} />
      <Label variant='overline'>{`Every ${row.label.toLowerCase()} (${row.instances.length})`}</Label>
      {row.instances.length === 0 && (
        <Muted variant='caption'>None stands in this world yet.</Muted>
      )}
      <PagedList
        items={row.instances}
        initial={6}
        noun={['building', 'buildings']}
        className='flex min-w-0 flex-col gap-2'
        itemKey={(item) => item.node.id}
      >
        {(item) => (
          <RecordRow
            icon={spec.icon}
            tone={spec.tone ?? 'muted'}
            title={<Ref node={item.node} />}
            caption={
              <>
                {`Level ${item.level} · ${STATES[item.state]}`}
                {item.town && (
                  <>
                    {' · in '}
                    <Ref node={item.town} />
                  </>
                )}
              </>
            }
          />
        )}
      </PagedList>
    </div>
  )
}

function DwellingType({
  row,
}: {
  row: NonNullable<
    ReturnType<typeof useStructureTypes>['data']
  >['dwellings'][number]
}) {
  const spec = HOUSING[row.housing]
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <PageHeader
        eyebrow='Home type'
        title={spec.label}
        description='Homes rise a level when their district’s services are met and its land is worth it, and fall when the services fail; set a district’s homes in its town’s city plan.'
        icon={DWELLING_ICON}
      />
      <Preview
        look={[{ ...HOUSING_LOOK[row.housing], scale: 1 }]}
        label={`The look of ${spec.label.toLowerCase()}`}
        icon={spec.icon}
      />
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <KpiTile
          label='Homes'
          value={row.dwellings}
          icon={Home}
          tone='success'
        />
        <KpiTile
          label='Districts'
          value={row.districts}
          icon={Users}
          tone='info'
        />
      </div>
      <Label variant='overline'>{`Towns with ${spec.label.toLowerCase()} (${row.towns.length})`}</Label>
      {row.towns.length === 0 && (
        <Muted variant='caption'>No district has homes of this kind yet.</Muted>
      )}
      <PagedList
        items={row.towns}
        initial={6}
        noun={['town', 'towns']}
        className='flex min-w-0 flex-col gap-2'
        itemKey={(item) => item.id}
      >
        {(item) => (
          <RecordRow
            icon={spec.icon}
            tone={spec.tone}
            title={<Ref node={item} />}
            caption='Open it to see and set its districts’ homes'
          />
        )}
      </PagedList>
    </div>
  )
}

export function TypePage({ selection }: { selection: TypeSelection }) {
  const query = useStructureTypes(selection.worldId)
  if (query.isPending) return <LoadingBlock label='Reading the type' />
  if (query.isError)
    return (
      <EmptyState
        icon={DWELLING_ICON}
        title='The type could not be read'
        description={query.error.message}
      />
    )
  if (selection.kind === 'building') {
    const row = query.data.structures.find(
      (item) => item.kind === selection.type
    )
    return row ? (
      <BuildingType row={row} worldId={selection.worldId} />
    ) : (
      <EmptyState
        icon={DWELLING_ICON}
        title='No such type'
        description='This building type is not known.'
      />
    )
  }
  const row = query.data.dwellings.find(
    (item) => item.housing === selection.type
  )
  return row ? (
    <DwellingType row={row} />
  ) : (
    <EmptyState
      icon={DWELLING_ICON}
      title='No such type'
      description='This home type is not known.'
    />
  )
}
