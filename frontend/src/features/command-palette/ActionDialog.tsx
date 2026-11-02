import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Play } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
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
import { Text } from '@/components/typography'
import { toastWithUndo } from '@/features/ledger/undoToast'
import { type ActionItem, useRunAction } from './api'
import {
  type FieldValues,
  type FormField,
  buildPayload,
  fieldsOf,
  humanizeName,
  initialValues,
  routeFor,
} from './schemaForm'

const UNSET = '__unset'

function FieldControl({
  field,
  id,
  value,
  onChange,
}: {
  field: FormField
  id: string
  value: string | boolean | string[]
  onChange: (value: string | boolean | string[]) => void
}) {
  if (field.kind === 'boolean')
    return (
      <Switch id={id} checked={value === true} onCheckedChange={onChange} />
    )
  if (field.kind === 'enum')
    return (
      <Select
        value={typeof value === 'string' && value !== '' ? value : UNSET}
        onValueChange={(next) => onChange(next === UNSET ? '' : next)}
      >
        <SelectTrigger id={id} className='w-full'>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {!field.required && <SelectItem value={UNSET}>Not set</SelectItem>}
          {field.options.map((option) => (
            <SelectItem key={option} value={option}>
              {humanizeName(option)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    )
  if (field.kind === 'enum-list') {
    const chosen = Array.isArray(value) ? value : []
    return (
      <div id={id} className='flex min-w-0 flex-wrap gap-x-4 gap-y-2'>
        {field.options.map((option) => (
          <div key={option} className='flex items-center gap-2'>
            <Checkbox
              id={`${id}-${option}`}
              checked={chosen.includes(option)}
              onCheckedChange={(checked) =>
                onChange(
                  checked === true
                    ? [...chosen, option]
                    : chosen.filter((item) => item !== option)
                )
              }
            />
            <FieldLabel htmlFor={`${id}-${option}`}>
              {humanizeName(option)}
            </FieldLabel>
          </div>
        ))}
      </div>
    )
  }
  const text = typeof value === 'string' ? value : ''
  if (field.kind === 'json')
    return (
      <Textarea
        id={id}
        value={text}
        onChange={(event) => onChange(event.target.value)}
      />
    )
  return (
    <Input
      id={id}
      type={
        field.kind === 'integer' || field.kind === 'number' ? 'number' : 'text'
      }
      inputMode={field.kind === 'integer' ? 'numeric' : undefined}
      placeholder={
        field.kind.endsWith('-list') ? 'Separate items with commas' : undefined
      }
      value={text}
      required={field.required}
      onChange={(event) => onChange(event.target.value)}
    />
  )
}

type ActionDialogProps = {
  action: ActionItem | null
  onClose: () => void
}

function ActionForm({
  action,
  onClose,
}: {
  action: ActionItem
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const run = useRunAction()
  const fields = fieldsOf(action.input_schema)
  const [values, setValues] = useState<FieldValues>(() => initialValues(fields))
  const [typed, setTyped] = useState('')
  const [error, setError] = useState<string | null>(null)
  const needsWord =
    action.confirmation !== null &&
    fields.some((field) => field.name === 'confirm')
  const submit = () => {
    const built = buildPayload(
      fields,
      needsWord ? { ...values, confirm: typed.trim() } : values
    )
    if ('error' in built) {
      setError(built.error)
      return
    }
    const route = routeFor(action.path, built.payload)
    if ('error' in route) {
      setError(route.error)
      return
    }
    run.mutate(
      { method: action.method, url: route.url, body: route.body },
      {
        onSuccess: (result) => {
          onClose()
          if (result?.job_id)
            toast.success(result.message || `${action.title} started`)
          else
            toastWithUndo(
              queryClient,
              result?.message || `${action.title} done`,
              result?.ledger_entry_id
            )
        },
        onError: (failure) => setError(failure.message),
      }
    )
  }
  return (
    <form
      className='flex min-w-0 flex-col gap-4'
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
    >
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Badge variant='outline'>{humanizeName(action.group)}</Badge>
        <Badge variant='secondary'>{action.cost}</Badge>
        {action.mode === 'job' && (
          <Badge variant='outline'>Runs as a job</Badge>
        )}
      </div>
      <div className='flex max-h-96 min-w-0 flex-col gap-3 overflow-y-auto'>
        {fields.length === 0 && <Text>This action needs no input.</Text>}
        {fields
          .filter((field) => !(needsWord && field.name === 'confirm'))
          .map((field) => (
            <FormRow
              key={field.name}
              label={field.required ? `${field.label} *` : field.label}
            >
              {(id) => (
                <FieldControl
                  field={field}
                  id={id}
                  value={values[field.name]}
                  onChange={(next) => {
                    setError(null)
                    setValues((current) => ({ ...current, [field.name]: next }))
                  }}
                />
              )}
            </FormRow>
          ))}
        {needsWord && (
          <FormRow label={`Type ${action.confirmation} to confirm`}>
            {(id) => (
              <Input
                id={id}
                autoComplete='off'
                value={typed}
                onChange={(event) => setTyped(event.target.value)}
              />
            )}
          </FormRow>
        )}
      </div>
      {error && (
        <Text tone='destructive' role='alert'>
          {error}
        </Text>
      )}
      <DialogFooter>
        <Button type='button' variant='outline' onClick={onClose}>
          Cancel
        </Button>
        <Button
          type='submit'
          disabled={
            run.isPending || (needsWord && typed.trim() !== action.confirmation)
          }
          disabledReason={
            run.isPending
              ? 'Running'
              : `Type ${action.confirmation ?? ''} first`
          }
        >
          <Play />
          Run
        </Button>
      </DialogFooter>
    </form>
  )
}

export function ActionDialog({ action, onClose }: ActionDialogProps) {
  return (
    <Dialog open={action !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        {action && (
          <>
            <DialogHeader>
              <DialogTitle>{action.title}</DialogTitle>
              <DialogDescription>
                {action.mode === 'ledgered'
                  ? 'Written to the ledger; you can undo it.'
                  : 'A background job; its progress shows in the live feed.'}
              </DialogDescription>
            </DialogHeader>
            <ActionForm key={action.id} action={action} onClose={onClose} />
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
