import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { FormRow } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label } from '@/components/typography'
import { type EntityContext } from './context'
import { type PickerData, type PickerSpec, optionsFor } from './pickers'
import {
  type FieldMap,
  type FieldModel,
  type FieldValue,
  humanize,
} from './schema'

const NONE = '__none__'

type ActionFieldProps = {
  field: FieldModel
  label?: string
  value: FieldValue
  onChange: (value: FieldValue) => void
  picker?: PickerSpec
  multiline?: boolean
  ctx: EntityContext
  data: PickerData
  disabled?: boolean
}

function numberOrNull(raw: string): number | null {
  if (raw.trim() === '') return null
  const value = Number(raw)
  return Number.isFinite(value) ? value : null
}

function MapField({
  field,
  value,
  onChange,
  disabled,
}: {
  field: Extract<FieldModel, { kind: 'map' }>
  value: FieldMap
  onChange: (value: FieldValue) => void
  disabled?: boolean
}) {
  return (
    <div className='grid w-full min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
      {field.keys.map((key) => (
        <div key={key} className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor={`${field.key}-${key}`} truncate>
            {humanize(key)}
          </Label>
          <Input
            id={`${field.key}-${key}`}
            type='number'
            inputMode='numeric'
            disabled={disabled}
            value={value[key] ?? ''}
            onChange={(event) => {
              const next = { ...value }
              const parsed = numberOrNull(event.target.value)
              if (parsed === null) delete next[key]
              else next[key] = parsed
              onChange(next)
            }}
          />
        </div>
      ))}
    </div>
  )
}

export function ActionField({
  field,
  label,
  value,
  onChange,
  picker,
  multiline = false,
  ctx,
  data,
  disabled = false,
}: ActionFieldProps) {
  const title = label ?? humanize(field.key)
  const optional = !field.required && field.kind !== 'boolean'
  const description = optional ? 'Optional' : undefined
  return (
    <FormRow label={title} description={description}>
      {(id) => {
        if (picker) {
          const options = optionsFor(picker, ctx, data)
          return (
            <RecordCombobox
              id={id}
              options={options}
              value={value === null ? null : String(value)}
              onChange={(next) => onChange(next === null ? null : Number(next))}
              placeholder={options.length ? 'Choose' : 'Nothing to choose'}
              disabled={disabled || options.length === 0}
              disabledReason={
                options.length === 0
                  ? 'There is nothing to choose yet.'
                  : undefined
              }
              clearable={optional}
              aria-label={title}
            />
          )
        }
        switch (field.kind) {
          case 'enum':
            return (
              <Select
                value={value === null ? NONE : String(value)}
                onValueChange={(next) => onChange(next === NONE ? null : next)}
                disabled={disabled}
              >
                <SelectTrigger id={id} className='w-full'>
                  <SelectValue placeholder='Choose' />
                </SelectTrigger>
                <SelectContent>
                  {!field.required && (
                    <SelectItem value={NONE}>Let the world decide</SelectItem>
                  )}
                  {field.options.map((option) => (
                    <SelectItem key={option} value={option}>
                      {humanize(option)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )
          case 'boolean':
            return (
              <Switch
                id={id}
                checked={value === true}
                disabled={disabled}
                onCheckedChange={(checked) => onChange(checked)}
              />
            )
          case 'integer':
          case 'number':
            return (
              <Input
                id={id}
                type='number'
                inputMode='numeric'
                min={field.min}
                max={field.max}
                step={field.kind === 'integer' ? 1 : 'any'}
                disabled={disabled}
                value={typeof value === 'number' ? value : ''}
                onChange={(event) => onChange(numberOrNull(event.target.value))}
              />
            )
          case 'string':
            return multiline ? (
              <Textarea
                id={id}
                maxLength={field.maxLength}
                disabled={disabled}
                value={typeof value === 'string' ? value : ''}
                onChange={(event) => onChange(event.target.value)}
              />
            ) : (
              <Input
                id={id}
                maxLength={field.maxLength}
                disabled={disabled}
                value={typeof value === 'string' ? value : ''}
                onChange={(event) => onChange(event.target.value)}
              />
            )
          case 'map':
            return (
              <MapField
                field={field}
                value={(value as FieldMap | null) ?? {}}
                onChange={onChange}
                disabled={disabled}
              />
            )
          default:
            return null
        }
      }}
    </FormRow>
  )
}
