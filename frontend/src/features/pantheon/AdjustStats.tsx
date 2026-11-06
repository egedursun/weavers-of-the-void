import { useState } from 'react'
import { Check, SlidersHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Label, Muted } from '@/components/typography'
import { type ActionResponse } from './api'
import { useGodGate } from './gate'
import { useGodAction } from './godAction'

export type AdjustField = {
  key: string
  label: string
  value: number
  min: number
  max?: number
}

export type AdjustGroup = {
  title: string
  fields: AdjustField[]
}

type Change = { key: string; value: number }

type AdjustStatsProps = {
  id: string
  groups: AdjustGroup[]
  note?: string
  inline?: boolean
  run: (change: Change) => Promise<ActionResponse>
}

function range(field: AdjustField): string {
  return field.max === undefined ? `${field.min}+` : `${field.min}–${field.max}`
}

function problem(field: AdjustField, parsed: number | null): string | null {
  if (parsed === null || !Number.isInteger(parsed))
    return 'Write a whole number.'
  if (parsed < field.min || (field.max !== undefined && parsed > field.max))
    return `Must be ${range(field)}.`
  if (parsed === field.value) return 'This is the present value.'
  return null
}

function FieldEditor({
  id,
  field,
  blocked,
  pending,
  onSet,
}: {
  id: string
  field: AdjustField
  blocked: string | null
  pending: boolean
  onSet: (value: number) => void
}) {
  const [draft, setDraft] = useState(String(field.value))
  const parsed = draft.trim() === '' ? null : Number(draft)
  const reason =
    blocked ?? problem(field, parsed) ?? (pending ? 'Working on it.' : null)
  const inputId = `${id}-${field.key}`
  return (
    <form
      className='flex min-w-0 items-end gap-2'
      onSubmit={(event) => {
        event.preventDefault()
        if (reason === null && parsed !== null) onSet(parsed)
      }}
    >
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <Label as='label' htmlFor={inputId} truncate>
          {`${field.label} (${range(field)})`}
        </Label>
        <Input
          id={inputId}
          type='number'
          inputMode='numeric'
          min={field.min}
          max={field.max}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
      </div>
      <Button
        type='submit'
        variant='outline'
        size='icon'
        aria-label={`Set ${field.label}`}
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
      >
        <Check />
      </Button>
    </form>
  )
}

export function AdjustStats({
  id,
  groups,
  note,
  inline,
  run,
}: AdjustStatsProps) {
  const { reason } = useGodGate()
  const labels = new Map(
    groups.flatMap((group) => group.fields.map((field) => [field.key, field]))
  )
  const save = useGodAction({
    run,
    success: (_result, change: Change) =>
      `${labels.get(change.key)?.label ?? change.key} set`,
  })
  const blocked = reason()
  const fields = (
    <>
      {groups
        .filter((group) => group.fields.length > 0)
        .map((group) => (
          <div key={group.title} className='flex min-w-0 flex-col gap-3'>
            <Label variant='overline'>{group.title}</Label>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
              {group.fields.map((field) => (
                <FieldEditor
                  key={`${field.key}-${field.value}`}
                  id={id}
                  field={field}
                  blocked={blocked}
                  pending={save.isPending && save.variables?.key === field.key}
                  onSet={(value) => save.mutate({ key: field.key, value })}
                />
              ))}
            </div>
          </div>
        ))}
      {note && <Muted variant='caption'>{note}</Muted>}
    </>
  )
  if (inline) return <div className='flex min-w-0 flex-col gap-4'>{fields}</div>
  return (
    <Collapsible className='flex min-w-0 flex-col gap-3'>
      <CollapsibleTrigger asChild>
        <Button variant='outline' className='self-start'>
          <SlidersHorizontal />
          Adjust stats
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-4'>
        {fields}
      </CollapsibleContent>
    </Collapsible>
  )
}
