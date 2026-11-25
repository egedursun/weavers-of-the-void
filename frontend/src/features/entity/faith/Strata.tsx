import { useState } from 'react'
import { Ban, DoorClosed, DoorOpen, Save, Trash2, Unlink } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { funeralCustomValues, tenetKindValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { PagedList, FieldTile } from '@/components/domain'
import { Label, Text } from '@/components/typography'
import { useCosmography } from '@/features/cosmography/api'
import { useSons } from '@/features/pantheon/api'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { type Named, named } from '../realm/labels'
import { AdjustPanel, NumberField, RecordField } from '../realm/parts'
import { type Stratum } from './api'
import { CRITERIA_FLOORS, RITES, TENETS } from './labels'

const WORKING = 'Working…'
const ANY_GOD = 'any'
const NO_DIMENSION = 'none'
const PERCENT = 100

type Criteria = Stratum['criteria']
type FloorKey =
  | 'score_at_least'
  | 'score_below'
  | 'renown_at_least'
  | 'honour_at_least'
  | 'faith_at_least'
  | 'violence_at_least'
  | 'infamy_at_least'

const FLOORS: [FloorKey, string][] = [
  ['score_at_least', 'Score at least'],
  ['score_below', 'Score below'],
  ...Object.entries(CRITERIA_FLOORS).map(
    ([key, spec]) => [key as FloorKey, spec.label] as [FloorKey, string]
  ),
]

function busyOf(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function numberOrNull(text: string): number | null {
  if (text.trim() === '') return null
  const value = Math.round(Number(text))
  return Number.isFinite(value)
    ? Math.max(0, Math.min(PERCENT + 1, value))
    : null
}

function Toggles({
  label,
  values,
  chosen,
  table,
  blocked,
  onToggle,
}: {
  label: string
  values: readonly string[]
  chosen: readonly string[]
  table: Record<string, Named>
  blocked: string | null
  onToggle: (value: string) => void
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <Label>{label}</Label>
      <PagedList
        items={values}
        initial={12}
        noun={['entry', 'entries']}
        as='div'
        className='flex min-w-0 flex-wrap gap-1.5'
        itemKey={(value) => value}
      >
        {(value) => (
          <Button
            key={value}
            size='sm'
            variant={chosen.includes(value) ? 'default' : 'outline'}
            aria-pressed={chosen.includes(value)}
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => onToggle(value)}
          >
            {named(table, value).label}
          </Button>
        )}
      </PagedList>
    </div>
  )
}

export function StratumEditor({
  realmId,
  stratum,
  blocked,
}: {
  realmId: number
  stratum: Stratum
  blocked: string | null
}) {
  const sons = useSons()
  const criteria = stratum.criteria
  const [name, setName] = useState(stratum.name)
  const [priority, setPriority] = useState(String(criteria.priority ?? 50))
  const [floors, setFloors] = useState<Record<FloorKey, string>>(
    () =>
      Object.fromEntries(
        FLOORS.map(([key]) => [
          key,
          criteria[key] == null ? '' : String(criteria[key]),
        ])
      ) as Record<FloorKey, string>
  )
  const [noGod, setNoGod] = useState(Boolean(criteria.no_god))
  const [needsRite, setNeedsRite] = useState(Boolean(criteria.needs_rite))
  const [rites, setRites] = useState<string[]>([...(criteria.rites ?? [])])
  const [tenets, setTenets] = useState<string[]>([
    ...(criteria.tenets_any ?? []),
  ])
  const [son, setSon] = useState<string>(
    stratum.son_id === null ? ANY_GOD : String(stratum.son_id)
  )
  const [cult, setCult] = useState<number | null>(stratum.cult?.id ?? null)
  const heavens = useCosmography()
  const [dimension, setDimension] = useState<string>(
    stratum.dimension ? String(stratum.dimension.id) : NO_DIMENSION
  )
  const toggle =
    (setter: (update: (current: string[]) => string[]) => void) =>
    (value: string) =>
      setter((current) =>
        current.includes(value)
          ? current.filter((item) => item !== value)
          : [...current, value]
      )
  const rule: Criteria = {
    priority: Math.max(0, Math.round(Number(priority) || 0)),
    no_god: noGod,
    needs_rite: needsRite,
    ...Object.fromEntries(
      FLOORS.map(([key]) => [key, numberOrNull(floors[key])])
    ),
    rites: rites as Criteria['rites'],
    tenets_any: tenets as Criteria['tenets_any'],
  }
  const save = useGodAction({
    writes: [{ lever: 'afterlife:stratum' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/afterlife:stratum', {
          body: {
            realm_id: realmId,
            stratum_id: stratum.id,
            kind: stratum.kind,
            name,
            criteria: rule,
            son_id: son === ANY_GOD ? null : Number(son),
            cult_id: cult,
            closed: null,
            clear_links: son === ANY_GOD && cult === null,
            dimension_id: dimension === NO_DIMENSION ? null : Number(dimension),
            clear_dimension: dimension === NO_DIMENSION,
            remove: false,
          },
        })
      ),
  })
  const close = useGodAction<boolean>({
    writes: [{ lever: 'afterlife:stratum' }],
    run: (closed) =>
      unwrap(
        api.POST('/api/actions/afterlife:stratum', {
          body: {
            realm_id: realmId,
            stratum_id: stratum.id,
            kind: stratum.kind,
            closed,
            clear_links: false,
            clear_dimension: false,
            remove: false,
          },
        })
      ),
  })
  const unmake = useGodAction({
    writes: [{ lever: 'afterlife:stratum' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/afterlife:stratum', {
          body: {
            realm_id: realmId,
            stratum_id: stratum.id,
            kind: stratum.kind,
            clear_links: false,
            clear_dimension: false,
            remove: true,
          },
        })
      ),
  })
  const busy = busyOf(
    blocked,
    save.isPending,
    close.isPending,
    unmake.isPending
  )
  return (
    <AdjustPanel
      acts={[save, close, unmake]}
      trigger='Shape the stratum'
      title='Who this stratum takes'
      note='Strata are tried in order of priority, lowest first; a soul goes to the first whose every rule it meets. A closed stratum takes no one.'
    >
      <div data-surface='StratumEditor' className='flex min-w-0 flex-col gap-3'>
        <div className='grid min-w-0 grid-cols-1 gap-3 @md/soul:grid-cols-2'>
          <FieldTile label='Name'>
            <Input
              value={name}
              aria-label='Name'
              onChange={(event) => setName(event.target.value)}
            />
          </FieldTile>
          <NumberField
            label='Priority'
            min={0}
            value={priority}
            blocked={busy}
            onChange={setPriority}
          />
        </div>
        <div className='grid min-w-0 grid-cols-2 gap-2 @md/soul:grid-cols-4'>
          {FLOORS.map(([key, label]) => (
            <NumberField
              key={key}
              label={label}
              min={0}
              max={PERCENT + 1}
              placeholder='Any'
              value={floors[key]}
              blocked={busy}
              onChange={(value) =>
                setFloors((current) => ({ ...current, [key]: value }))
              }
            />
          ))}
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-4'>
          <label className='flex items-center gap-2'>
            <Switch
              checked={noGod}
              disabled={busy !== null}
              aria-label='Only the godless'
              onCheckedChange={setNoGod}
            />
            <Text as='span'>Only the godless</Text>
          </label>
          <label className='flex items-center gap-2'>
            <Switch
              checked={needsRite}
              disabled={busy !== null}
              aria-label='Only those given their rites'
              onCheckedChange={setNeedsRite}
            />
            <Text as='span'>Only those given their rites</Text>
          </label>
        </div>
        <Toggles
          label='Only these rites'
          values={funeralCustomValues}
          chosen={rites}
          table={RITES}
          blocked={busy}
          onToggle={toggle(setRites)}
        />
        <Toggles
          label='Only if the faith holds one of'
          values={tenetKindValues}
          chosen={tenets}
          table={TENETS}
          blocked={busy}
          onToggle={toggle(setTenets)}
        />
        <div className='grid min-w-0 grid-cols-1 gap-3 @md/soul:grid-cols-2'>
          <MindPicker
            label='Ruled by'
            value={son}
            table={{
              [ANY_GOD]: 'Any god',
              ...Object.fromEntries(
                (sons.data ?? []).map((item) => [
                  String(item.son.id),
                  item.son.name,
                ])
              ),
            }}
            blocked={busy}
            onPick={setSon}
          />
          <RecordField
            label='Claimed by the church'
            types={['cult']}
            value={cult}
            onChange={setCult}
            blocked={busy}
            placeholder='Any church'
          />
          <MindPicker
            label='Lies in the dimension'
            value={dimension}
            table={{
              [NO_DIMENSION]: 'No dimension of its own',
              ...Object.fromEntries(
                (heavens.data?.dimensions ?? []).map((item) => [
                  String(item.id),
                  item.name,
                ])
              ),
            }}
            blocked={busy}
            onPick={setDimension}
          />
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            act={save}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => save.mutate(undefined)}
          >
            <Save />
            Set the rules
          </Button>
          {(stratum.son_id !== null || stratum.cult) && (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => {
                setSon(ANY_GOD)
                setCult(null)
              }}
            >
              <Unlink />
              Open to every god
            </Button>
          )}
          <Button
            act={close}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => close.mutate(!stratum.closed)}
          >
            {stratum.closed ? <DoorOpen /> : <DoorClosed />}
            {stratum.closed ? 'Open its gates' : 'Close its gates'}
          </Button>
          <Button
            act={unmake}
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => unmake.mutate(undefined)}
          >
            {stratum.population > 0 ? <Ban /> : <Trash2 />}
            Unmake it
          </Button>
        </div>
      </div>
    </AdjustPanel>
  )
}
