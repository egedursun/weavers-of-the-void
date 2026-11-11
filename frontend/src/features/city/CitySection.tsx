import { Suspense, lazy, useState } from 'react'
import {
  ArrowDown,
  ArrowUp,
  Hammer,
  Home,
  Move,
  Plus,
  Shield,
  Tent,
  Trash2,
  Unlock,
  Users,
  Wrench,
  X,
} from 'lucide-react'
import { postAction } from '@/api/actions'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import {
  Chip,
  Facts,
  ForgeCard,
  Meter,
  RecordRow,
} from '@/features/cosmography/parts'
import { hasWebGL2 } from '@/features/cosmos/useCosmosViewSettings'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { DISTRICT_SPEC } from '@/features/entity/society/labels'
import { KIND_SPEC } from '@/features/entity/society/structureLabels'
import { Ref } from '@/features/gatherings/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { HOUSING, MORPHOLOGIES, SERVICES } from '@/features/urban/labels'
import { CityPlan2D } from './CityPlan2D'
import { type CityPick } from './CityScene3D'
import {
  type CityBuilding,
  type CityDistrict,
  type CityScene,
  useCityScene,
} from './api'
import { CIVIC, CITY_ICON, STATES, ZONES } from './labels'

const CityScene3D = lazy(() => import('./CityScene3D'))
const MAX_LEVEL = 5

function ZoneLegend({ scene }: { scene: CityScene }) {
  return (
    <PagedList
      items={scene.zones}
      initial={7}
      noun={['zone', 'zones']}
      as='div'
      className='flex min-w-0 flex-wrap gap-2'
      listProps={{ role: 'group', 'aria-label': 'Zones of the city' }}
      itemKey={(zone) => zone.zone}
    >
      {(zone) => {
        const spec = ZONES[zone.zone]
        return (
          <Chip icon={spec.icon}>
            {`${spec.label}: ${zone.districts} districts, ${zone.cells} hexes, ${zone.buildings} buildings`}
          </Chip>
        )
      }}
    </PagedList>
  )
}

function DistrictPanel({
  district,
  blocked,
  moving,
  onMove,
  onClose,
}: {
  district: CityDistrict
  blocked: string | null
  moving: boolean
  onMove: () => void
  onClose: () => void
}) {
  const [kind, setKind] = useState<string>(district.kind)
  const edit = useGodAction({
    run: (body: { level?: number; kind?: CityDistrict['kind'] }) =>
      postAction('district:edit', {
        district_id: district.id,
        clear_design: false,
        release: [],
        ...body,
      }),
    success: 'The district is set so',
  })
  const [housing, setHousing] = useState<string>(district.housing)
  const homes = useGodAction({
    run: (body: { values: { housing?: string }; release: string[] }) =>
      postAction('district_urban:edit', { district_id: district.id, ...body }),
    success: 'The district is set so',
  })
  const raze = useGodAction({
    run: () => postAction('district:raze', { district_id: district.id }),
    success: 'The district is razed',
  })
  const busy = why(blocked, edit.isPending, raze.isPending, homes.isPending)
  const spec = DISTRICT_SPEC[district.kind]
  const zone = ZONES[district.zone]
  return (
    <RecordRow
      icon={spec.icon}
      tone={spec.tone ?? 'muted'}
      title={`${spec.label} · ${zone.label}`}
      caption={`Level ${district.level}, hex ${district.q}, ${district.r} · ${district.cells.length} hexes · ${district.residents} people in ${district.dwellings} homes (${HOUSING[district.housing].label.toLowerCase()})`}
      aside={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Close the district'
          onClick={onClose}
        >
          <X />
        </Button>
      }
    >
      <Facts
        items={[
          ['Condition', `${district.condition}%`],
          ['Desirability', district.desirability],
          ['Land value', district.land_value],
          ['Criminal hold', district.turf],
          [
            'Held values',
            district.locked.length ? district.locked.join(', ') : 'none',
          ],
        ]}
      />
      {district.services.map((row) => (
        <Meter
          key={row.service}
          label={`${SERVICES[row.service].label} reach`}
          value={row.coverage}
          tone='info'
        />
      ))}
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <Button
          size='sm'
          disabled={busy !== null || district.level >= MAX_LEVEL}
          disabledReason={
            busy ??
            (district.level >= MAX_LEVEL
              ? 'The district is at its highest level'
              : undefined)
          }
          onClick={() => edit.mutate({ level: district.level + 1 })}
        >
          <ArrowUp />
          Raise a level
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || district.level <= 1}
          disabledReason={
            busy ??
            (district.level <= 1
              ? 'The district is at its lowest level'
              : undefined)
          }
          onClick={() => edit.mutate({ level: district.level - 1 })}
        >
          <ArrowDown />
          Lower a level
        </Button>
        <Button
          size='sm'
          variant={moving ? 'default' : 'outline'}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={onMove}
        >
          <Move />
          {moving ? 'Pick a hex in the scene' : 'Move to another hex'}
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || district.locked.length === 0}
          disabledReason={
            busy ??
            (district.locked.length === 0
              ? 'The engine holds nothing of this district'
              : undefined)
          }
          onClick={() =>
            homes.mutate({ values: {}, release: [...district.locked] })
          }
        >
          <Unlock />
          Release to the engine
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => raze.mutate()}
        >
          <Trash2 />
          Raze
        </Button>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <MindPicker
          label='Rezone as'
          value={kind}
          table={table(DISTRICT_SPEC)}
          blocked={busy}
          onPick={setKind}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || kind === district.kind}
          disabledReason={
            busy ??
            (kind === district.kind ? 'Choose another kind first' : undefined)
          }
          onClick={() => edit.mutate({ kind: kind as CityDistrict['kind'] })}
        >
          <Wrench />
          Rezone
        </Button>
        <MindPicker
          label='Homes'
          value={housing}
          table={table(HOUSING)}
          blocked={busy}
          onPick={setHousing}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || housing === district.housing}
          disabledReason={
            busy ??
            (housing === district.housing
              ? 'Choose another kind of home first'
              : undefined)
          }
          onClick={() => homes.mutate({ values: { housing }, release: [] })}
        >
          <Home />
          Set and hold the homes
        </Button>
      </div>
    </RecordRow>
  )
}

function BuildingPanel({
  building,
  districts,
  blocked,
  onClose,
}: {
  building: CityBuilding
  districts: CityDistrict[]
  blocked: string | null
  onClose: () => void
}) {
  const [target, setTarget] = useState<string>(
    building.district_id ? String(building.district_id) : ''
  )
  const [harm, setHarm] = useState('20')
  const finish = useGodAction({
    run: () =>
      postAction('structure:finish', { structure_id: building.node.id }),
    success: 'The work is finished',
  })
  const repair = useGodAction({
    run: () =>
      postAction('structure:repair', { structure_id: building.node.id }),
    success: 'The work is repaired',
  })
  const damage = useGodAction({
    run: () =>
      postAction('structure:damage', {
        structure_id: building.node.id,
        amount: Math.max(1, Math.min(100, Number(harm) || 1)),
        cause: '',
      }),
    success: 'The work is struck',
  })
  const raze = useGodAction({
    run: () =>
      postAction('structure:raze', {
        structure_id: building.node.id,
        reason: '',
      }),
    success: 'The work is razed',
  })
  const place = useGodAction({
    run: () =>
      postAction('structure:place', {
        structure_id: building.node.id,
        district_id: target ? Number(target) : null,
      }),
    success: 'The work stands in that district',
  })
  const busy = why(
    blocked,
    finish.isPending,
    repair.isPending,
    damage.isPending,
    raze.isPending,
    place.isPending
  )
  const spec = KIND_SPEC[building.kind]
  const zone = ZONES[building.zone]
  const unfinished =
    building.state === 'planned' || building.state === 'building'
  const whole = building.state === 'complete' && building.condition >= 100
  return (
    <RecordRow
      icon={spec.icon}
      tone={spec.tone ?? 'muted'}
      title={<Ref node={building.node} />}
      caption={`${spec.label} · ${zone.label}${building.civic ? ` · ${CIVIC[building.civic].label}` : ''}${building.service ? ` · serves ${SERVICES[building.service].label.toLowerCase()}` : ''} · ${STATES[building.state]}`}
      aside={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Close the building'
          onClick={onClose}
        >
          <X />
        </Button>
      }
    >
      <Facts
        items={[
          ['Level', building.level],
          ['Condition', `${building.condition}%`],
          ['Staffed', `${building.staff_pct}%`],
          ['Stands at', `hex ${building.q}, ${building.r}`],
        ]}
      />
      {unfinished && (
        <Meter label='Built' value={building.progress} tone='warning' />
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <Button
          size='sm'
          disabled={busy !== null || !unfinished}
          disabledReason={
            busy ?? (!unfinished ? 'It is already built' : undefined)
          }
          onClick={() => finish.mutate()}
        >
          <Hammer />
          Finish now
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || whole}
          disabledReason={busy ?? (whole ? 'It is whole' : undefined)}
          onClick={() => repair.mutate()}
        >
          <Wrench />
          Repair
        </Button>
        <NumberField
          label='Harm (1–100)'
          min={1}
          max={100}
          value={harm}
          blocked={busy}
          onChange={setHarm}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => damage.mutate()}
        >
          <Shield />
          Strike it
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => raze.mutate()}
        >
          <Trash2 />
          Raze
        </Button>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <MindPicker
          label='Stands in'
          value={target}
          table={Object.fromEntries(
            districts.map((item) => [
              String(item.id),
              `${DISTRICT_SPEC[item.kind].label} (hex ${item.q}, ${item.r})`,
            ])
          )}
          blocked={
            busy ??
            (districts.length === 0 ? 'The town has no districts yet' : null)
          }
          onPick={setTarget}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={
            busy !== null || target === String(building.district_id ?? '')
          }
          disabledReason={
            busy ??
            (target === String(building.district_id ?? '')
              ? 'Choose another district first'
              : undefined)
          }
          onClick={() => place.mutate()}
        >
          <Move />
          Place it there
        </Button>
      </div>
    </RecordRow>
  )
}

function BuildForge({
  scene,
  blocked,
}: {
  scene: CityScene
  blocked: string | null
}) {
  const [district, setDistrict] = useState('residential')
  const [kind, setKind] = useState('school')
  const [level, setLevel] = useState('1')
  const found = useGodAction({
    run: () =>
      postAction('district:build', {
        settlement_id: scene.town.id,
        kind: district as CityDistrict['kind'],
        material: 'timber',
      }),
    success: 'The district is raised',
  })
  const commission = useGodAction({
    run: () =>
      postAction('structure:commission', {
        site_id: scene.town.id,
        kind: kind as CityBuilding['kind'],
        level: Math.max(1, Math.min(5, Number(level) || 1)),
        funds: 0,
      }),
    success: 'The work is begun',
  })
  const busy = why(blocked, found.isPending, commission.isPending)
  return (
    <ForgeCard
      icon={Plus}
      tone='gold'
      title='Build in the city'
      note='Raise a district of any zone, or set a work to be built; the planner gives it its hex by its zone and the town’s growth pattern.'
      columns={4}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => found.mutate()}
          >
            <Plus />
            Raise the district
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => commission.mutate()}
          >
            <Hammer />
            Begin the work
          </Button>
        </div>
      }
    >
      <MindPicker
        label='District'
        value={district}
        table={table(DISTRICT_SPEC)}
        blocked={blocked}
        onPick={setDistrict}
      />
      <MindPicker
        label='Work'
        value={kind}
        table={table(KIND_SPEC)}
        blocked={blocked}
        onPick={setKind}
      />
      <NumberField
        label='Level (1–5)'
        min={1}
        max={5}
        value={level}
        blocked={blocked}
        onChange={setLevel}
      />
    </ForgeCard>
  )
}

function CityBody({
  scene,
  blocked,
}: {
  scene: CityScene
  blocked: string | null
}) {
  const [selected, setSelected] = useState<CityPick>(null)
  const [moving, setMoving] = useState<number | null>(null)
  const move = useGodAction({
    run: (cell: { q: number; r: number }) =>
      postAction('district:move', {
        district_id: moving ?? 0,
        q: cell.q,
        r: cell.r,
      }),
    success: () => {
      setMoving(null)
      return 'The district is moved'
    },
  })
  const pick = (next: CityPick) => {
    if (next?.kind === 'cell' && moving !== null) {
      move.mutate({ q: next.q, r: next.r })
      return
    }
    setSelected(next)
  }
  const district =
    selected?.kind === 'district'
      ? scene.districts.find((item) => item.id === selected.id)
      : undefined
  const building =
    selected?.kind === 'building'
      ? scene.buildings.find((item) => item.node.id === selected.id)
      : undefined
  const homes = scene.districts.reduce((sum, item) => sum + item.dwellings, 0)
  const plan = <CityPlan2D scene={scene} selected={selected} onPick={pick} />
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <KpiTile
          label='People'
          value={scene.population}
          icon={Users}
          tone='info'
        />
        <KpiTile label='Homes' value={homes} icon={Home} tone='success' />
        <KpiTile
          label='Homeless'
          value={scene.homeless}
          icon={Tent}
          tone='danger'
        />
        <KpiTile
          label='Buildings'
          value={scene.buildings.length}
          icon={CITY_ICON}
          tone='gold'
        />
      </div>
      <ZoneLegend scene={scene} />
      <Muted variant='caption'>
        {`A ${scene.tier.replaceAll('_', ' ')} of ${MORPHOLOGIES[scene.morphology].label.toLowerCase()} growth; walls of level ${scene.walls_level}${scene.walls_radius ? ` at ${scene.walls_radius} hexes out` : ''}; roads of level ${scene.roads}; water from ${scene.water.replaceAll('_', ' ')}. Each house drawn stands for ${scene.scale} homes, each shelter for ${scene.scale} homeless households.`}
      </Muted>
      <div className='relative min-w-0 overflow-hidden rounded-xl border bg-muted'>
        <div className='aspect-video w-full'>
          {scene.districts.length === 0 && scene.buildings.length === 0 ? (
            <EmptyState
              icon={CITY_ICON}
              size='inline'
              title='Nothing is built here yet'
              description='Raise a district or begin a work below.'
            />
          ) : hasWebGL2() ? (
            <Suspense fallback={plan}>
              <CityScene3D
                scene={scene}
                selected={selected}
                moving={moving}
                onPick={pick}
                fallback={plan}
              />
            </Suspense>
          ) : (
            plan
          )}
        </div>
      </div>
      {moving !== null && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Text variant='caption'>Choose the hex the district moves to.</Text>
          <Button size='sm' variant='ghost' onClick={() => setMoving(null)}>
            <X />
            Stop moving
          </Button>
        </div>
      )}
      {district && (
        <DistrictPanel
          district={district}
          blocked={why(blocked, move.isPending)}
          moving={moving === district.id}
          onMove={() => setMoving(moving === district.id ? null : district.id)}
          onClose={() => setSelected(null)}
        />
      )}
      {building && (
        <BuildingPanel
          building={building}
          districts={scene.districts}
          blocked={blocked}
          onClose={() => setSelected(null)}
        />
      )}
      <BuildForge scene={scene} blocked={blocked} />
      <Label variant='overline'>{`Districts (${scene.districts.length})`}</Label>
      <PagedList
        items={scene.districts}
        initial={4}
        noun={['district', 'districts']}
        className='flex min-w-0 flex-col gap-2'
        itemKey={(row) => row.id}
      >
        {(row) => {
          const spec = DISTRICT_SPEC[row.kind]
          return (
            <RecordRow
              icon={spec.icon}
              tone={spec.tone ?? 'muted'}
              title={`${spec.label} · level ${row.level}`}
              caption={`${ZONES[row.zone].label} · ${row.dwellings} homes · desirability ${row.desirability}`}
              aside={
                <Button
                  size='sm'
                  variant='ghost'
                  onClick={() => setSelected({ kind: 'district', id: row.id })}
                >
                  Show
                </Button>
              }
            />
          )
        }}
      </PagedList>
      <Label variant='overline'>{`Buildings (${scene.buildings.length})`}</Label>
      <PagedList
        items={scene.buildings}
        initial={4}
        noun={['building', 'buildings']}
        className='flex min-w-0 flex-col gap-2'
        itemKey={(row) => row.node.id}
      >
        {(row) => {
          const spec = KIND_SPEC[row.kind]
          return (
            <RecordRow
              icon={spec.icon}
              tone={spec.tone ?? 'muted'}
              title={<Ref node={row.node} />}
              caption={`${spec.label} · ${ZONES[row.zone].label} · ${STATES[row.state]}`}
              aside={
                <Button
                  size='sm'
                  variant='ghost'
                  onClick={() =>
                    setSelected({ kind: 'building', id: row.node.id })
                  }
                >
                  Show
                </Button>
              }
            />
          )
        }}
      </PagedList>
    </div>
  )
}

export function CitySection({
  settlementId,
  readOnlyReason = null,
}: {
  settlementId: number
  readOnlyReason?: string | null
}) {
  const query = useCityScene(settlementId)
  return (
    <Section
      id='section-city'
      title='The city'
      description='The town drawn from the engine itself: its zones and districts on their hexes, every building at its stage, its homes and homeless, its walls and water; and the god’s hand to raise, rezone, move, build and raze.'
      icon={CITY_ICON}
      tone='gold'
    >
      <div data-surface='CitySection' className='flex min-w-0 flex-col gap-3'>
        {query.isPending ? (
          <LoadingBlock label='Drawing the city' />
        ) : query.isError ? (
          <EmptyState
            icon={CITY_ICON}
            size='inline'
            title='The city could not be drawn'
            description={query.error.message}
          />
        ) : (
          <CityBody scene={query.data} blocked={readOnlyReason} />
        )}
      </div>
    </Section>
  )
}
