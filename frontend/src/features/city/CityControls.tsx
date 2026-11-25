import { useState } from 'react'
import {
  ArrowDown,
  ArrowUp,
  Hammer,
  Home,
  Move,
  Plus,
  Shield,
  Trash2,
  Unlock,
  Users,
  Wrench,
  X,
} from 'lucide-react'
import { postAction } from '@/api/actions'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Text } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import {
  Facts,
  ForgeCard,
  Meter,
  RecordRow,
} from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { DISTRICT_SPEC } from '@/features/entity/society/labels'
import { KIND_SPEC } from '@/features/entity/society/structureLabels'
import { Ref } from '@/features/gatherings/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { HOUSING, SERVICES } from '@/features/urban/labels'
import { type CityBuilding, type CityDistrict, type CityScene } from './api'
import { CIVIC, STATES, ZONES } from './labels'

const MAX_LEVEL = 5

export function DistrictPanel({
  district,
  castes,
  blocked,
  moving,
  onMove,
  onClose,
}: {
  district: CityDistrict
  castes: CityScene['castes']
  blocked: string | null
  moving: boolean
  onMove: () => void
  onClose: () => void
}) {
  const [kind, setKind] = useState<string>(district.kind)
  const edit = useGodAction({
    writes: [{ lever: 'district:edit' }],
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
  const [caste, setCaste] = useState<string>(
    district.caste ? String(district.caste.id) : ''
  )
  const homes = useGodAction({
    writes: [{ lever: 'district_urban:edit' }],
    run: (body: {
      values: { housing?: string; purity_rank_id?: number }
      release: string[]
    }) =>
      postAction('district_urban:edit', { district_id: district.id, ...body }),
    success: 'The district is set so',
  })
  const raze = useGodAction({
    writes: [{ lever: 'district:raze' }],
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
      caption={`Level ${district.level}, hex ${district.q}, ${district.r} · ${plural(district.cells.length, 'hex', 'hexes')} · ${plural(district.residents, 'person', 'people')} in ${plural(district.dwellings, 'home', 'homes')} (${HOUSING[district.housing].label.toLowerCase()})`}
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
            'Caste quarter',
            district.caste
              ? `${district.caste.name} (standing ${district.caste.standing})`
              : 'none',
          ],
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
          act={edit}
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
          act={edit}
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
          act={homes}
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
          act={raze}
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
          act={edit}
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
          act={homes}
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
        <MindPicker
          label='Quarter of the caste'
          value={caste}
          table={Object.fromEntries(
            castes.map((row) => [String(row.id), row.name])
          )}
          blocked={
            castes.length === 0 ? "The town's people keep no castes" : busy
          }
          placeholder='Pick a caste'
          onPick={setCaste}
        />
        <Button
          act={homes}
          size='sm'
          variant='outline'
          disabled={
            busy !== null ||
            castes.length === 0 ||
            caste === '' ||
            caste === String(district.caste?.id ?? '')
          }
          disabledReason={
            busy ??
            (castes.length === 0
              ? "The town's people keep no castes"
              : caste === '' || caste === String(district.caste?.id ?? '')
                ? 'Choose another caste first'
                : undefined)
          }
          onClick={() =>
            homes.mutate({
              values: { purity_rank_id: Number(caste) },
              release: [],
            })
          }
        >
          <Users />
          Make it their quarter and hold it
        </Button>
      </div>
    </RecordRow>
  )
}

export function BuildingPanel({
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
    building.home_district_id ? String(building.home_district_id) : ''
  )
  const [harm, setHarm] = useState('20')
  const finish = useGodAction({
    writes: [{ lever: 'structure:finish' }],
    run: () =>
      postAction('structure:finish', { structure_id: building.node.id }),
    success: 'The work is finished',
  })
  const repair = useGodAction({
    writes: [{ lever: 'structure:repair' }],
    run: () =>
      postAction('structure:repair', { structure_id: building.node.id }),
    success: 'The work is repaired',
  })
  const damage = useGodAction({
    writes: [{ lever: 'structure:damage' }],
    run: () =>
      postAction('structure:damage', {
        structure_id: building.node.id,
        amount: Math.max(1, Math.min(100, Number(harm) || 1)),
        cause: '',
      }),
    success: 'The work is struck',
  })
  const raze = useGodAction({
    writes: [{ lever: 'structure:raze' }],
    run: () =>
      postAction('structure:raze', {
        structure_id: building.node.id,
        reason: '',
      }),
    success: 'The work is razed',
  })
  const place = useGodAction({
    writes: [{ lever: 'structure:place' }],
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
  const home = districts.find((item) => item.id === building.home_district_id)
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
      <Text variant='caption' tone='muted'>
        {home
          ? `Stands in the ${DISTRICT_SPEC[home.kind].label.toLowerCase()}${building.district_id === null ? ', where the engine settles it next epoch' : ''}.`
          : 'Stands in no district yet; the engine settles it when the town has one.'}
      </Text>
      {unfinished && (
        <Meter label='Built' value={building.progress} tone='warning' />
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <Button
          act={finish}
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
          act={repair}
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
          act={damage}
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
          act={raze}
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
          act={place}
          size='sm'
          variant='outline'
          disabled={
            busy !== null || target === String(building.home_district_id ?? '')
          }
          disabledReason={
            busy ??
            (target === String(building.home_district_id ?? '')
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

export function BuildForge({
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
    writes: [{ lever: 'district:build' }],
    run: () =>
      postAction('district:build', {
        settlement_id: scene.town.id,
        kind: district as CityDistrict['kind'],
        material: 'timber',
      }),
    success: 'The district is raised',
  })
  const commission = useGodAction({
    writes: [{ lever: 'structure:commission' }],
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
            act={found}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => found.mutate()}
          >
            <Plus />
            Raise the district
          </Button>
          <Button
            act={commission}
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
