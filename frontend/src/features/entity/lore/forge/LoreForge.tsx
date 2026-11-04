import { useState } from 'react'
import { Anvil, Check } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { EntityLink, FormRow } from '@/components/domain'
import { Muted } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useWorldState } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { ChoicePicker, NamedChip } from '../LoreFields'
import { MAX_POWER, busyOf } from '../model'
import {
  FORGE_FIELDS,
  FORGE_KIND,
  type ForgeDraft,
  type ForgeField,
  type ForgeKind,
  forgeValues,
  initialDraft,
  missingField,
} from './forgeModel'

const PLACES = [
  'settlement',
  'region',
  'place',
  'people',
  'cult',
  'faction',
  'polity',
  'structure',
  'mortal',
] as const
const DEFAULT_POWER = 3

function MultiField({
  field,
  value,
  blocked,
  onChange,
}: {
  field: Extract<ForgeField, { kind: 'multi' }>
  value: string[]
  blocked: string | null
  onChange: (next: string[]) => void
}) {
  return (
    <div className='min-w-0 sm:col-span-2'>
      <FormRow label={field.label}>
        {() => (
          <div className='flex min-w-0 flex-wrap gap-2'>
            {Object.entries(field.table).map(([key, spec]) => {
              const on = value.includes(key)
              return (
                <Button
                  key={key}
                  size='sm'
                  variant={on ? 'default' : 'outline'}
                  aria-pressed={on}
                  disabled={blocked !== null}
                  disabledReason={blocked ?? undefined}
                  onClick={() =>
                    onChange(
                      on
                        ? value.filter((item) => item !== key)
                        : [...value, key]
                    )
                  }
                >
                  <spec.icon aria-hidden='true' />
                  {spec.label}
                </Button>
              )
            })}
          </div>
        )}
      </FormRow>
    </div>
  )
}

function DraftField({
  field,
  draft,
  blocked,
  put,
}: {
  field: ForgeField
  draft: ForgeDraft
  blocked: string | null
  put: (key: string, value: string | number | string[]) => void
}) {
  const value = draft[field.key]
  if (field.kind === 'enum')
    return (
      <ChoicePicker
        label={field.label}
        value={String(value ?? '')}
        table={field.table}
        blocked={blocked}
        placeholder='Choose'
        onPick={(next) => put(field.key, next)}
      />
    )
  if (field.kind === 'multi')
    return (
      <MultiField
        field={field}
        value={Array.isArray(value) ? value : []}
        blocked={blocked}
        onChange={(next) => put(field.key, next)}
      />
    )
  return (
    <FormRow label={`${field.label} (${field.min}–${field.max})`}>
      {(id) => (
        <Input
          id={id}
          type='number'
          min={field.min}
          max={field.max}
          value={String(value ?? field.initial)}
          onChange={(event) =>
            put(field.key, Math.round(Number(event.target.value) || 0))
          }
        />
      )}
    </FormRow>
  )
}

export function LoreForge({
  kind,
  fields,
  worldId,
  locationId,
  triggerLabel,
  onCreated,
}: {
  kind: ForgeKind
  fields?: readonly ForgeField[]
  worldId?: number | null
  locationId?: number | null
  triggerLabel?: string
  onCreated?: (id: number) => void
}) {
  const spec = FORGE_KIND[kind]
  const typed = fields ?? FORGE_FIELDS[kind]
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [power, setPower] = useState(DEFAULT_POWER)
  const [place, setPlace] = useState<number | null>(locationId ?? null)
  const [world, setWorld] = useState<string>(worldId ? String(worldId) : '')
  const [draft, setDraft] = useState<ForgeDraft>(() => initialDraft(typed))
  const [made, setMade] = useState<{ id: number; name: string } | null>(null)
  const state = useWorldState()
  const worlds = state.data?.worlds ?? []
  const { reason } = useGodGate()
  const forge = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/lore:create', {
          body: {
            entity_type: kind,
            name: name.trim(),
            description: description.trim(),
            world_id: world ? Number(world) : null,
            location_id: place,
            power,
            values: forgeValues(typed, draft) as Record<string, never>,
          },
        })
      ),
    onDone: (result) => {
      const id = result.created_ids?.[0]
      if (typeof id === 'number') {
        setMade({ id, name: name.trim() })
        onCreated?.(id)
      }
      setName('')
      setDescription('')
      setDraft(initialDraft(typed))
    },
  })
  const missing = missingField(typed, draft)
  const where =
    place === null && !world && worlds.length !== 1
      ? 'Choose where it belongs'
      : null
  const blocked = busyOf(
    reason() ??
      (name.trim() ? null : 'Name it first') ??
      (missing ? `Choose the ${missing.label.toLowerCase()}` : null) ??
      where,
    forge.isPending
  )
  const Icon = spec.icon
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) setMade(null)
        if (next && !world && worlds.length === 1)
          setWorld(String(worlds[0].id))
      }}
    >
      <DialogTrigger asChild>
        <Button size='sm' variant='outline' data-surface='LoreForge'>
          <Anvil />
          {triggerLabel ?? `Forge a new ${spec.label.toLowerCase()}`}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className='flex items-center gap-2'>
            <Icon aria-hidden='true' />
            {`Forge a new ${spec.label.toLowerCase()}`}
          </DialogTitle>
          <DialogDescription>
            Shape it by hand: it enters the world at once with every value you
            set here, and the change can be undone from the ledger.
          </DialogDescription>
        </DialogHeader>
        <div className='flex min-w-0 flex-col gap-3'>
          <FormRow label='Name'>
            {(id) => (
              <Input
                id={id}
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            )}
          </FormRow>
          <FormRow label='What it is'>
            {(id) => (
              <Textarea
                id={id}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            )}
          </FormRow>
          <div className='grid min-w-0 grid-cols-1 items-start gap-3 sm:grid-cols-2'>
            {typed.map((field) => (
              <DraftField
                key={field.key}
                field={field}
                draft={draft}
                blocked={forge.isPending ? 'Working…' : null}
                put={(key, value) =>
                  setDraft((before) => ({ ...before, [key]: value }))
                }
              />
            ))}
            <FormRow label={`Weight in the world (1–${MAX_POWER})`}>
              {(id) => (
                <Input
                  id={id}
                  type='number'
                  min={1}
                  max={MAX_POWER}
                  value={String(power)}
                  onChange={(event) =>
                    setPower(Math.round(Number(event.target.value) || 1))
                  }
                />
              )}
            </FormRow>
          </div>
          <FormRow label='Where it belongs'>
            {() => (
              <EntityPicker
                types={[...PLACES]}
                value={place}
                onChange={setPlace}
                placeholder='Choose a place, people or holder…'
              />
            )}
          </FormRow>
          {place === null && worlds.length > 1 && (
            <FormRow label='World'>
              {(id) => (
                <Select value={world} onValueChange={setWorld}>
                  <SelectTrigger id={id} className='w-full'>
                    <SelectValue placeholder='Choose a world' />
                  </SelectTrigger>
                  <SelectContent>
                    {worlds.map((entry) => (
                      <SelectItem key={entry.id} value={String(entry.id)}>
                        {entry.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </FormRow>
          )}
          {made && (
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Badge variant='default'>
                <Check aria-hidden='true' />
                Made
              </Badge>
              <EntityLink kind='entity' id={String(made.id)}>
                {made.name}
              </EntityLink>
            </div>
          )}
          {blocked && !forge.isPending && (
            <Muted variant='caption'>{blocked}</Muted>
          )}
          {typed.length > 0 && (
            <div className='flex min-w-0 flex-wrap gap-2'>
              {typed
                .filter((field) => field.kind === 'enum' && draft[field.key])
                .map((field) =>
                  field.kind === 'enum' ? (
                    <NamedChip
                      key={field.key}
                      spec={field.table[String(draft[field.key])]}
                    />
                  ) : null
                )}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => forge.mutate()}
          >
            <Anvil />
            Forge it
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
