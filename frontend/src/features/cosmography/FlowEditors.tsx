import { useState } from 'react'
import { Boxes, Gauge, Plus, Trash2, Users } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import type { components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Switch } from '@/components/ui/switch'
import { PagedList } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { COMMODITY, MATERIAL_LABEL } from '@/features/entity/economy/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { CLASS_SPEC } from '@/features/entity/society/labels'
import { NumberField } from '@/features/entity/wilds/parts'
import {
  type JourneyRecord,
  type RouteRecord,
  useCosmographyAction,
} from './api'
import { SCOPES } from './labels'
import { Chip, Meter, RecordEditor, RecordPick } from './parts'

type Cargo = components['schemas']['CargoLine']
type Passenger = components['schemas']['PassengerLine']
type CommodityKind = components['schemas']['CommodityKind']
type MaterialKind = components['schemas']['MaterialKind']
type SocialClass = components['schemas']['SocialClass']
type Edit = { values: EditValues; release: string[] }
type Load = {
  convoy?: number
  escorts?: number
  cargo?: Cargo[]
  passengers?: Passenger[]
}

const COMMODITY_NAMES = Object.fromEntries(
  Object.entries(COMMODITY).map(([key, value]) => [key, value.label])
)
const CLASS_NAMES = Object.fromEntries(
  Object.entries(CLASS_SPEC).map(([key, value]) => [key, value.label])
)

export function RouteScopeChip({ route }: { route: RouteRecord }) {
  if (!route.scope) return null
  const scope = SCOPES[route.scope]
  return <Chip icon={scope.icon}>{scope.label}</Chip>
}

export function RouteFlowEditor({ route }: { route: RouteRecord }) {
  const [keeper, setKeeper] = useState<number | null>(null)
  const edit = useCosmographyAction(
    'route_flow:edit',
    (vars: Edit) => ({ route_id: route.id, ...vars }),
    'The flow of the route is set'
  )
  const busy = edit.isPending ? 'Working' : null
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant='ghost' size='sm'>
          <Gauge />
          Flow
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align='start'
        className='flex w-full max-w-md flex-col gap-3'
      >
        <div
          id='section-route-flow'
          data-surface='RouteFlowEditor'
          className='flex min-w-0 flex-col gap-3'
        >
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Text weight='semibold'>Flow of the route</Text>
            <RouteScopeChip route={route} />
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            <Meter
              label={`Traffic ${route.traffic} of ${route.capacity}`}
              value={route.traffic}
              max={Math.max(route.capacity, 1)}
              tone='info'
            />
            <Meter label='Wear' value={route.wear} tone='warning' />
            <Meter label='Piracy' value={route.piracy} tone='destructive' />
            <Meter label='Toll' value={route.toll_pct} tone='warning' />
          </div>
          <Muted variant='caption'>
            {route.window_every > 0
              ? `Opens once every ${plural(route.window_every, 'epoch', 'epochs')}, offset ${route.window_offset}.`
              : 'Always open while its state allows.'}
          </Muted>
          <RecordEditor
            title='Set the flow'
            note='Values you set are held. A window of 0 keeps the route open every epoch.'
            fields={[
              { key: 'capacity', label: 'Capacity', kind: 'number', min: 1 },
              { key: 'traffic', label: 'Traffic', kind: 'number', min: 0 },
              {
                key: 'toll_pct',
                label: 'Toll',
                kind: 'number',
                min: 0,
                max: 100,
              },
              {
                key: 'piracy',
                label: 'Piracy',
                kind: 'number',
                min: 0,
                max: 100,
              },
              { key: 'wear', label: 'Wear', kind: 'number', min: 0, max: 100 },
              {
                key: 'window_every',
                label: 'Opens every',
                kind: 'number',
                min: 0,
              },
              {
                key: 'window_offset',
                label: 'Window offset',
                kind: 'number',
                min: 0,
              },
            ]}
            locked={route.locked ?? []}
            busy={busy}
            onSave={(values) => edit.mutate({ values, release: [] })}
            onRelease={(release) => edit.mutate({ values: {}, release })}
          />
          <div className='flex min-w-0 flex-col items-stretch gap-2 rounded-lg border bg-muted/20 p-3'>
            <RecordPick
              label='Toll keeper'
              types={['polity', 'people', 'organization', 'company']}
              value={keeper}
              onChange={setKeeper}
            />
            <Button
              size='sm'
              disabled={
                busy !== null ||
                (keeper === null && route.toll_controller_entity_id === null)
              }
              disabledReason={
                busy ??
                (keeper === null && route.toll_controller_entity_id === null
                  ? 'Choose a keeper first'
                  : undefined)
              }
              onClick={() =>
                edit.mutate({
                  values: { toll_controller_entity_id: keeper },
                  release: [],
                })
              }
            >
              {keeper === null ? 'Free the toll' : 'Give the toll'}
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}

function CargoForm({
  busy,
  onAdd,
}: {
  busy: string | null
  onAdd: (line: Cargo) => void
}) {
  const [commodity, setCommodity] = useState('')
  const [material, setMaterial] = useState('')
  const [amount, setAmount] = useState('10')
  const missing = commodity === '' ? 'Choose a good first' : null
  return (
    <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-4'>
      <MindPicker
        label='Good'
        value={commodity}
        table={COMMODITY_NAMES}
        blocked={busy}
        onPick={setCommodity}
      />
      <MindPicker
        label='Material'
        value={material}
        table={MATERIAL_LABEL}
        blocked={busy}
        onPick={setMaterial}
      />
      <NumberField
        label='Amount'
        value={amount}
        min={0}
        disabled={busy !== null}
        onChange={setAmount}
      />
      <Button
        size='sm'
        disabled={busy !== null || missing !== null}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() =>
          onAdd({
            commodity: commodity as CommodityKind,
            material: material === '' ? null : (material as MaterialKind),
            amount: Math.max(Number(amount) || 0, 0),
            item_entity_id: null,
          })
        }
      >
        <Plus />
        Load it
      </Button>
    </div>
  )
}

function PassengerForm({
  busy,
  onAdd,
}: {
  busy: string | null
  onAdd: (line: Passenger) => void
}) {
  const [social, setSocial] = useState('')
  const [count, setCount] = useState('10')
  const [condition, setCondition] = useState('100')
  const [sick, setSick] = useState(false)
  const missing = social === '' ? 'Choose a class first' : null
  return (
    <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-5'>
      <MindPicker
        label='Class'
        value={social}
        table={CLASS_NAMES}
        blocked={busy}
        onPick={setSocial}
      />
      <NumberField
        label='Count'
        value={count}
        min={0}
        disabled={busy !== null}
        onChange={setCount}
      />
      <NumberField
        label='Condition'
        value={condition}
        min={0}
        max={100}
        disabled={busy !== null}
        onChange={setCondition}
      />
      <label className='flex min-w-0 items-center gap-2'>
        <Switch
          checked={sick}
          onCheckedChange={setSick}
          aria-label='Carrying sickness'
          disabled={busy !== null}
        />
        <Text as='span'>Sick</Text>
      </label>
      <Button
        size='sm'
        disabled={busy !== null || missing !== null}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() =>
          onAdd({
            community_entity_id: null,
            social_class: social as SocialClass,
            count: Math.max(Number(count) || 0, 0),
            condition: Math.min(Math.max(Number(condition) || 0, 0), 100),
            sick,
          })
        }
      >
        <Plus />
        Board them
      </Button>
    </div>
  )
}

export function JourneyLoadEditor({ journey }: { journey: JourneyRecord }) {
  const [convoy, setConvoy] = useState(String(journey.convoy))
  const [escorts, setEscorts] = useState(String(journey.escorts))
  const load = useCosmographyAction(
    'journey:load',
    (vars: Load) => ({ journey_id: journey.id, ...vars }),
    'The load of the voyage is set'
  )
  const release = useCosmographyAction(
    'journey:release',
    (fields: string[]) => ({ journey_id: journey.id, fields }),
    'The voyage loads itself again'
  )
  const busy = load.isPending || release.isPending ? 'Working' : null
  const cargo = journey.cargo ?? []
  const passengers = journey.passengers ?? []
  const locked = journey.locked ?? []
  const convoyValue = Number(convoy)
  const escortValue = Number(escorts)
  const sizeInvalid =
    !Number.isInteger(convoyValue) ||
    convoyValue < 1 ||
    !Number.isInteger(escortValue) ||
    escortValue < 0
      ? 'A convoy needs at least one ship and no fewer than 0 escorts'
      : null
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant='ghost' size='sm'>
          <Boxes />
          Load
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align='start'
        className='flex w-full max-w-lg flex-col gap-3'
      >
        <div
          id='section-journey-load'
          data-surface='JourneyLoadEditor'
          className='flex min-w-0 flex-col gap-3'
        >
          <Text weight='semibold'>What the voyage carries</Text>
          <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
            <NumberField
              label='Ships in the convoy'
              value={convoy}
              min={1}
              disabled={busy !== null}
              onChange={setConvoy}
            />
            <NumberField
              label='Escorts'
              value={escorts}
              min={0}
              disabled={busy !== null}
              onChange={setEscorts}
            />
            <Button
              size='sm'
              disabled={busy !== null || sizeInvalid !== null}
              disabledReason={busy ?? sizeInvalid ?? undefined}
              onClick={() =>
                load.mutate({ convoy: convoyValue, escorts: escortValue })
              }
            >
              Hold the convoy
            </Button>
          </div>
          <div className='flex min-w-0 flex-col gap-2'>
            <Muted variant='caption'>Cargo</Muted>
            {cargo.length === 0 ? (
              <Muted variant='caption'>It carries no goods.</Muted>
            ) : (
              <PagedList
                items={cargo}
                initial={12}
                noun={['entry', 'entries']}
                as='ul'
                className='flex min-w-0 flex-wrap gap-1'
                itemKey={(line, at) =>
                  `${line.commodity}-${line.material ?? ''}-${at}`
                }
              >
                {(line, at) => (
                  <li key={`${line.commodity}-${line.material ?? ''}-${at}`}>
                    <Button
                      size='sm'
                      variant='outline'
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      aria-label={`Unload ${COMMODITY[line.commodity].label}`}
                      onClick={() =>
                        load.mutate({
                          cargo: cargo.filter((_, other) => other !== at),
                        })
                      }
                    >
                      <Trash2 />
                      {`${COMMODITY[line.commodity].label}${line.material ? ` (${MATERIAL_LABEL[line.material]})` : ''} × ${line.amount}`}
                    </Button>
                  </li>
                )}
              </PagedList>
            )}
            <CargoForm
              busy={busy}
              onAdd={(line) => load.mutate({ cargo: [...cargo, line] })}
            />
          </div>
          <div className='flex min-w-0 flex-col gap-2'>
            <Muted variant='caption'>Passengers</Muted>
            {passengers.length === 0 ? (
              <Muted variant='caption'>It carries no passengers.</Muted>
            ) : (
              <PagedList
                items={passengers}
                initial={12}
                noun={['entry', 'entries']}
                as='ul'
                className='flex min-w-0 flex-wrap gap-1'
                itemKey={(line, at) => `${line.social_class}-${at}`}
              >
                {(line, at) => (
                  <li key={`${line.social_class}-${at}`}>
                    <Button
                      size='sm'
                      variant='outline'
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      aria-label={`Set ashore the ${CLASS_SPEC[line.social_class].label}`}
                      onClick={() =>
                        load.mutate({
                          passengers: passengers.filter(
                            (_, other) => other !== at
                          ),
                        })
                      }
                    >
                      <Users />
                      {`${CLASS_SPEC[line.social_class].label} × ${line.count} · ${line.condition}%${line.sick ? ' · sick' : ''}`}
                    </Button>
                  </li>
                )}
              </PagedList>
            )}
            <PassengerForm
              busy={busy}
              onAdd={(line) =>
                load.mutate({ passengers: [...passengers, line] })
              }
            />
          </div>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || locked.length === 0}
              disabledReason={
                busy ??
                (locked.length === 0
                  ? 'Nothing is held; the engine already loads this voyage'
                  : undefined)
              }
              onClick={() => release.mutate([...locked])}
            >
              Let the engine load it again
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
