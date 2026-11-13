import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import { Anvil, Building2, CookingPot, Plus, Shield, Truck } from 'lucide-react'
import {
  equipmentFamilyValues,
  structureKindValues,
  unitKindValues,
} from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { PagedList } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { ForgeCard } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { KIND_SPEC } from '@/features/entity/society/structureLabels'
import { type ThingKinds, useLever } from './api'
import { type MadeKind, kindKey } from './kindKeys'
import {
  COURSE,
  DISH_FOODS,
  FRAME_OPTIONS,
  METHOD,
  namedTable,
  wordTable,
} from './labels'

type Ref = ThingKinds['own']['vehicle_types'][number]

const FRAMES = wordTable(FRAME_OPTIONS)
const ROLES = wordTable(unitKindValues)
const FAMILIES = wordTable(equipmentFamilyValues)
const KINDS = Object.fromEntries(
  structureKindValues.map((kind) => [kind, KIND_SPEC[kind].label])
)
const FOODS = wordTable(DISH_FOODS)

function Kinds({
  title,
  kind,
  rows,
  worldId,
}: {
  title: string
  kind: MadeKind
  rows: Ref[]
  worldId: number | null
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <Label variant='overline'>{`${title} (${rows.length})`}</Label>
      {rows.length === 0 ? (
        <Muted variant='caption'>None of its own yet.</Muted>
      ) : (
        <PagedList
          items={rows}
          initial={12}
          noun={['type', 'types']}
          as='div'
          className='flex min-w-0 flex-wrap gap-1.5'
          itemKey={(row) => row.id}
        >
          {(row) =>
            worldId === null ? (
              <Badge
                key={row.id}
                size='sm'
                variant='outline'
              >{`${row.name} · ${row.family}`}</Badge>
            ) : (
              <Badge key={row.id} size='sm' variant='outline' asChild>
                <Link
                  to='/atlas'
                  search={{ select: kindKey(kind, worldId, row.id) }}
                >{`${row.name} · ${row.family}`}</Link>
              </Badge>
            )
          }
        </PagedList>
      )}
    </div>
  )
}

export function OwnKindsPanel({
  nodeId,
  data,
  blocked,
}: {
  nodeId: number
  data: ThingKinds
  blocked: string | null
}) {
  const [frame, setFrame] = useState('')
  const [role, setRole] = useState('')
  const [family, setFamily] = useState('')
  const [method, setMethod] = useState('')
  const [course, setCourse] = useState('staple')
  const [food, setFood] = useState('')
  const [building, setBuilding] = useState('')
  const world = data.world_id
  const vehicle = useLever(
    'design:draw',
    (_: void) => ({ owner_id: nodeId, world_id: world, frame: frame as never }),
    'The vehicle type is drawn'
  )
  const unit = useLever(
    'unit_type:create',
    (_: void) => ({ owner_id: nodeId, role: role as never }),
    'The kind of soldier is raised'
  )
  const model = useLever(
    'equipment_model:create',
    (_: void) => ({
      origin_id: nodeId,
      world_id: world,
      family: family as never,
    }),
    'The model is made'
  )
  const dish = useLever(
    'dish:create',
    (_: void) => ({
      origin_id: nodeId,
      world_id: world,
      method: method as never,
      course: course as never,
      ingredients: food ? [food as never] : [],
    }),
    'The dish is cooked'
  )
  const structure = useLever(
    'structure_design:create',
    (_: void) => ({
      world_id: world,
      values: {
        name: `${data.node.name} ${(KIND_SPEC as Record<string, { label: string } | undefined>)[building]?.label.toLowerCase() ?? 'work'}`,
        base_kind: building,
        origin_node_id: nodeId,
      },
    }),
    'The building type is drawn'
  )
  const busy = why(
    blocked,
    vehicle.isPending,
    unit.isPending,
    model.isPending,
    dish.isPending,
    structure.isPending
  )
  const need = (value: string, what: string) =>
    busy ?? (value ? null : `Pick ${what}`)
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Muted variant='caption'>
        The named types it made; each has its own page in the atlas. The
        vehicles, soldiers and goods built to them are held here, not entered in
        the atlas.
      </Muted>
      <Kinds
        title='Vehicle types'
        kind='vehicle'
        rows={data.own.vehicle_types}
        worldId={world}
      />
      <Kinds
        title='Kinds of soldier'
        kind='unit'
        rows={data.own.unit_types}
        worldId={world}
      />
      <Kinds
        title='Equipment models'
        kind='equipment'
        rows={data.own.equipment_models}
        worldId={world}
      />
      <Kinds
        title='Dishes'
        kind='dish'
        rows={data.own.dishes}
        worldId={world}
      />
      <Kinds
        title='Building types'
        kind='building'
        rows={data.own.building_types}
        worldId={world}
      />
      <ForgeCard
        icon={Plus}
        tone='gold'
        title='Give it a new kind'
        note='Make a type of its own: its name comes from its own tongue, its values from what it can make. Every value can then be set on its atlas page.'
        columns={4}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              disabled={need(frame, 'a frame') !== null}
              disabledReason={need(frame, 'a frame') ?? undefined}
              onClick={() => vehicle.mutate()}
            >
              <Truck />
              Draw the vehicle type
            </Button>
            <Button
              size='sm'
              disabled={need(role, 'a role') !== null}
              disabledReason={need(role, 'a role') ?? undefined}
              onClick={() => unit.mutate()}
            >
              <Shield />
              Raise the kind of soldier
            </Button>
            <Button
              size='sm'
              disabled={need(family, 'a family') !== null}
              disabledReason={need(family, 'a family') ?? undefined}
              onClick={() => model.mutate()}
            >
              <Anvil />
              Make the model
            </Button>
            <Button
              size='sm'
              disabled={need(method, 'a way of cooking') !== null}
              disabledReason={need(method, 'a way of cooking') ?? undefined}
              onClick={() => dish.mutate()}
            >
              <CookingPot />
              Cook the dish
            </Button>
            <Button
              size='sm'
              disabled={need(building, 'a kind of structure') !== null}
              disabledReason={
                need(building, 'a kind of structure') ?? undefined
              }
              onClick={() => structure.mutate()}
            >
              <Building2 />
              Draw the building type
            </Button>
          </div>
        }
      >
        <MindPicker
          label='Vehicle frame'
          value={frame}
          table={FRAMES}
          blocked={busy}
          onPick={setFrame}
        />
        <MindPicker
          label='Battlefield role'
          value={role}
          table={ROLES}
          blocked={busy}
          onPick={setRole}
        />
        <MindPicker
          label='Equipment family'
          value={family}
          table={FAMILIES}
          blocked={busy}
          onPick={setFamily}
        />
        <MindPicker
          label='Kind of structure'
          value={building}
          table={KINDS}
          blocked={busy}
          onPick={setBuilding}
        />
        <MindPicker
          label='Way of cooking'
          value={method}
          table={namedTable(METHOD)}
          blocked={busy}
          onPick={setMethod}
        />
        <MindPicker
          label='Course'
          value={course}
          table={namedTable(COURSE)}
          blocked={busy}
          onPick={setCourse}
        />
        <MindPicker
          label='Main food'
          value={food}
          table={FOODS}
          blocked={busy}
          onPick={setFood}
        />
      </ForgeCard>
    </div>
  )
}
