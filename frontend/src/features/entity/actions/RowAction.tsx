import { useMemo, useState } from 'react'
import { type LucideIcon } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { ConfirmDialog, FormRow } from '@/components/domain'
import { type ComboboxOption } from '@/components/domain/RecordCombobox'
import { Muted } from '@/components/typography'
import { useLoreMutation } from '../api/mutations'
import { useActionCatalogue } from '../api/queries'
import { CostChip } from './ActionCard'
import { ActionField } from './ActionField'
import { useEntityCtx } from './entityContext'
import { PENDING_REASON, fixedCost, useLoreGate } from './gate'
import { DEFAULT_PICKERS, type PickerSpec } from './pickers'
import { type CatalogueActionPath } from './registry'
import {
  type FieldModel,
  type FieldValue,
  bodyOf,
  fieldsOf,
  humanize,
  initialValue,
  missingRequired,
} from './schema'
import { usePickerData } from './usePickerData'

export type RowActionProps = {
  path: CatalogueActionPath
  icon: LucideIcon
  label: string
  fixed: Record<string, FieldValue>
  defaults?: Record<string, FieldValue>
  labels?: Record<string, string>
  pickers?: Record<string, PickerSpec>
  choices?: Record<string, ComboboxOption[]>
  hide?: readonly string[]
  multiline?: readonly string[]
  destructive?: boolean
  confirm?: string
  note?: string
  iconOnly?: boolean
  held?: readonly string[]
  params?: Record<string, ParamValue>
}

type ParamValue = number | string | boolean

function pickerOf(
  field: FieldModel,
  pickers: Record<string, PickerSpec> | undefined
): PickerSpec | undefined {
  if (field.kind !== 'integer' || !field.key.endsWith('_id')) return undefined
  return pickers?.[field.key] ?? DEFAULT_PICKERS[field.key]
}

export function RowAction({
  path,
  icon: Icon,
  label,
  fixed,
  defaults,
  labels,
  pickers,
  choices,
  hide = [],
  multiline = [],
  destructive = false,
  confirm,
  note,
  iconOnly = false,
  held = [],
  params,
}: RowActionProps) {
  const id = path.replace('/api/actions/', '')
  const catalogue = useActionCatalogue()
  const data = usePickerData()
  const ctx = useEntityCtx()
  const gate = useLoreGate()
  const item = catalogue.data?.find((entry) => entry.id === id)
  const fields = useMemo(
    () => (item ? fieldsOf(item.input_schema) : []),
    [item]
  )
  const skip = useMemo(
    () => new Set<string>([...Object.keys(fixed), ...hide]),
    [fixed, hide]
  )
  const shown = fields.filter(
    (field) => !skip.has(field.key) && field.kind !== 'unsupported'
  )
  const initial = useMemo(() => {
    const values: Record<string, FieldValue> = {}
    for (const field of fields) values[field.key] = initialValue(field)
    return { ...values, ...(defaults ?? {}) }
  }, [fields, defaults])
  const [open, setOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [values, setValues] = useState<Record<string, FieldValue> | null>(null)
  const [released, setReleased] = useState<string[]>([])
  const [paramValues, setParamValues] = useState<Record<
    string,
    ParamValue
  > | null>(null)
  const currentParams = paramValues ?? params ?? {}
  const paramKeys = Object.keys(params ?? {})
  const hasForm = shown.length > 0 || held.length > 0 || paramKeys.length > 0
  const current = values ?? initial
  const mutation = useLoreMutation({
    run: (body: Record<string, FieldValue | Record<string, ParamValue>>) =>
      unwrap(api.POST(path as never, { body } as never)),
    onDone: () => {
      setValues(null)
      setReleased([])
      setParamValues(null)
      setOpen(false)
    },
  })
  const missing = missingRequired(fields, current, skip)
  const blocked =
    (item ? null : 'Loading the action.') ??
    gate.reason({ cost: item ? fixedCost(item.cost) : null }) ??
    (missing
      ? `Fill in ${labels?.[missing.key] ?? humanize(missing.key)}.`
      : null) ??
    (mutation.isPending ? PENDING_REASON : null)
  const submit = () =>
    mutation.mutate({
      ...bodyOf(fields, current, skip),
      ...(held.length > 0 ? { release: released } : {}),
      ...(paramValues ? { params: paramValues } : {}),
      ...fixed,
    })
  const title = item?.title ?? label
  const trigger = (
    <Button
      size={iconOnly ? 'icon-sm' : 'sm'}
      variant={destructive ? 'destructive' : 'outline'}
      aria-label={label}
      disabled={blocked !== null && !hasForm}
      disabledReason={blocked !== null && !hasForm ? blocked : undefined}
      onClick={() => (!hasForm ? setConfirming(true) : setOpen(true))}
    >
      <Icon />
      {!iconOnly && label}
    </Button>
  )
  return (
    <>
      {trigger}
      {!hasForm ? (
        <ConfirmDialog
          open={confirming}
          onOpenChange={setConfirming}
          title={`${title}?`}
          desc={confirm ?? note ?? title}
          destructive={destructive}
          confirmText={label}
          isLoading={mutation.isPending}
          handleConfirm={() => {
            setConfirming(false)
            submit()
          }}
        />
      ) : (
        <Dialog
          open={open}
          onOpenChange={(next) => {
            setOpen(next)
            if (!next) setValues(null)
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{title}</DialogTitle>
              <DialogDescription>
                {note ?? 'Every change goes into the ledger and can be undone.'}
              </DialogDescription>
            </DialogHeader>
            <div className='flex min-w-0 flex-col gap-3'>
              {shown.map((field) => (
                <ActionField
                  key={field.key}
                  field={field}
                  label={labels?.[field.key]}
                  value={current[field.key] ?? null}
                  onChange={(value) =>
                    setValues({ ...current, [field.key]: value })
                  }
                  picker={pickerOf(field, pickers)}
                  options={choices?.[field.key]}
                  multiline={multiline.includes(field.key)}
                  ctx={ctx ?? undefined}
                  data={data}
                  disabled={mutation.isPending}
                />
              ))}
              {paramKeys.map((key) => {
                const value = currentParams[key]
                const change = (next: ParamValue) =>
                  setParamValues({ ...currentParams, [key]: next })
                return (
                  <FormRow key={key} label={labels?.[key] ?? humanize(key)}>
                    {(fieldId) =>
                      typeof value === 'boolean' ? (
                        <Switch
                          id={fieldId}
                          checked={value}
                          disabled={mutation.isPending}
                          onCheckedChange={change}
                        />
                      ) : typeof value === 'number' ? (
                        <Input
                          id={fieldId}
                          type='number'
                          inputMode='numeric'
                          disabled={mutation.isPending}
                          value={value}
                          onChange={(event) =>
                            change(Number(event.target.value) || 0)
                          }
                        />
                      ) : (
                        <Input
                          id={fieldId}
                          disabled={mutation.isPending}
                          value={value}
                          onChange={(event) => change(event.target.value)}
                        />
                      )
                    }
                  </FormRow>
                )
              })}
              {held.length > 0 && (
                <FormRow
                  label='Let the world change again'
                  description='Held values stay as you set them until released.'
                >
                  {(fieldId) => (
                    <ToggleGroup
                      id={fieldId}
                      type='multiple'
                      variant='outline'
                      size='sm'
                      className='flex-wrap justify-start'
                      value={released}
                      onValueChange={setReleased}
                      disabled={mutation.isPending}
                      aria-label='Values to release'
                    >
                      {held.map((key) => (
                        <ToggleGroupItem key={key} value={key}>
                          {labels?.[key] ?? humanize(key)}
                        </ToggleGroupItem>
                      ))}
                    </ToggleGroup>
                  )}
                </FormRow>
              )}
            </div>
            <DialogFooter>
              {item && <CostChip text={item.cost} />}
              {item && fixedCost(item.cost) === null && (
                <Muted variant='caption'>{`Cost: ${item.cost}`}</Muted>
              )}
              <Button
                variant={destructive ? 'destructive' : 'default'}
                disabled={blocked !== null}
                disabledReason={blocked ?? undefined}
                aria-busy={mutation.isPending || undefined}
                onClick={() => (confirm ? setConfirming(true) : submit())}
              >
                <Icon />
                {label}
              </Button>
            </DialogFooter>
          </DialogContent>
          {confirm && (
            <ConfirmDialog
              open={confirming}
              onOpenChange={setConfirming}
              title={`${title}?`}
              desc={confirm}
              destructive={destructive}
              confirmText={label}
              isLoading={mutation.isPending}
              handleConfirm={() => {
                setConfirming(false)
                submit()
              }}
            />
          )}
        </Dialog>
      )}
    </>
  )
}
