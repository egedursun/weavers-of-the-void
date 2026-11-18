import { useId, useState } from 'react'
import { Lock, Unlock, type LucideIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { ConfirmDialog, FieldTile } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { useNames } from '@/features/entity/api/queries'
import { MATERIAL_FAMILY, type MaterialKind, type Named } from './labels'
import { NONE, iconTone, useMaterialChoices } from './model'

export function HeldBadge({ held }: { held: boolean }) {
  if (!held) return null
  return (
    <Badge size='sm' variant='default'>
      <Lock />
      Held
    </Badge>
  )
}

export function ReleaseButton({
  held,
  busy,
  label = 'Release',
  onRelease,
}: {
  held: boolean
  busy: string | null
  label?: string
  onRelease: () => void
}) {
  if (!held) return null
  return (
    <Button
      size='sm'
      variant='outline'
      disabled={busy !== null}
      disabledReason={busy ?? undefined}
      onClick={onRelease}
    >
      <Unlock />
      {label}
    </Button>
  )
}

export function ConfirmButton({
  icon: Icon,
  label,
  title,
  description,
  confirm,
  busy,
  onConfirm,
}: {
  icon: LucideIcon
  label: string
  title: string
  description: string
  confirm: string
  busy: string | null
  onConfirm: () => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => setOpen(true)}
      >
        <Icon />
        {label}
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={title}
        desc={description}
        confirmText={confirm}
        destructive
        handleConfirm={() => {
          setOpen(false)
          onConfirm()
        }}
      />
    </>
  )
}

export function ChoiceSelect({
  label,
  value,
  table,
  blocked,
  placeholder,
  onPick,
}: {
  label: string
  value: string
  table: Record<string, Named>
  blocked: string | null
  placeholder?: string
  onPick: (value: string) => void
}) {
  const id = useId()
  return (
    <FieldTile id={id} label={label}>
      <Select value={value} onValueChange={onPick} disabled={blocked !== null}>
        <SelectTrigger id={id} aria-label={label} className='w-full'>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(table).map(([key, item]) => (
            <SelectItem key={key} value={key}>
              <item.icon aria-hidden='true' className={iconTone(item.tone)} />
              {item.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FieldTile>
  )
}

export function MaterialSelect({
  label,
  worldId,
  value,
  blocked,
  only,
  none,
  onPick,
}: {
  label: string
  worldId: number | null
  value: string
  blocked: string | null
  only?: readonly MaterialKind[]
  none?: string
  onPick: (value: string) => void
}) {
  const choices = useMaterialChoices(worldId, only)
  const table: Record<string, Named> = none
    ? {
        [NONE]: {
          label: none,
          icon: MATERIAL_FAMILY.stone.icon,
          tone: 'muted',
        },
        ...choices,
      }
    : choices
  return (
    <ChoiceSelect
      label={label}
      value={value}
      table={table}
      blocked={blocked}
      placeholder='Choose a material'
      onPick={onPick}
    />
  )
}

export function EntityChoice({
  label,
  types,
  value,
  blocked,
  worldId,
  placeholder,
  onChange,
}: {
  label: string
  types: readonly string[]
  value: string | null
  blocked: string | null
  worldId?: number | null
  placeholder: string
  onChange: (value: string | null) => void
}) {
  const id = useId()
  const names = useNames()
  const wanted = new Set(types)
  const options = (names.data ?? [])
    .filter(
      (row) =>
        row.kind === 'entity' &&
        wanted.has(row.type) &&
        (worldId === undefined || worldId === null || row.world_id === worldId)
    )
    .map((row) => ({
      value: String(row.id),
      label: row.name,
      hint: row.type.replaceAll('_', ' '),
    }))
  return (
    <FieldTile id={id} label={label}>
      <RecordCombobox
        id={id}
        options={options}
        value={value}
        onChange={(next) => onChange(next)}
        placeholder={names.isPending ? 'Loading names…' : placeholder}
        clearable
        maxShown={Math.max(1, options.length)}
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        aria-label={label}
      />
    </FieldTile>
  )
}

export function TextField({
  label,
  value,
  placeholder,
  disabled,
  onChange,
}: {
  label: string
  value: string
  placeholder?: string
  disabled?: boolean
  onChange: (value: string) => void
}) {
  const id = useId()
  return (
    <FieldTile id={id} label={label}>
      <Input
        id={id}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        aria-label={label}
        onChange={(event) => onChange(event.target.value)}
      />
    </FieldTile>
  )
}

export function NoteField({
  label,
  value,
  placeholder,
  disabled,
  onChange,
}: {
  label: string
  value: string
  placeholder?: string
  disabled?: boolean
  onChange: (value: string) => void
}) {
  const id = useId()
  return (
    <FieldTile id={id} label={label}>
      <Textarea
        id={id}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        aria-label={label}
        onChange={(event) => onChange(event.target.value)}
      />
    </FieldTile>
  )
}
