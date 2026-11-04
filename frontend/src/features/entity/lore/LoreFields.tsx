import { useState } from 'react'
import { Plus, Save, Trash2, Unlock } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Label, Text } from '@/components/typography'
import { MindPicker } from '../mind/parts'
import { type LoreValue, table, words } from './api'
import { busyOf, useLoreEdit } from './model'

export type FieldSpec =
  | {
      key: string
      kind: 'number'
      min?: number
      max?: number
      nullable?: boolean
    }
  | { key: string; kind: 'bool' }
  | { key: string; kind: 'text'; nullable?: boolean }
  | { key: string; kind: 'enum'; values: readonly string[] }

export type DictSpec = {
  key: string
  label: string
  value: Record<string, number | string>
}

function shown(value: unknown): string {
  return value === null || value === undefined ? '' : String(value)
}

function parsed(spec: FieldSpec, raw: string | boolean): LoreValue {
  if (spec.kind === 'bool') return Boolean(raw)
  if (spec.kind === 'number') {
    if (raw === '' && spec.nullable) return null
    return Math.round(Number(raw) || 0)
  }
  if (spec.kind === 'text' && raw === '' && spec.nullable) return null
  return String(raw)
}

export function LoreFields({
  entityId,
  surface,
  fields,
  current,
  locked,
  blocked,
}: {
  entityId: number
  surface: string
  fields: readonly FieldSpec[]
  current: Readonly<Record<string, unknown>>
  locked: readonly string[]
  blocked: string | null
}) {
  const [draft, setDraft] = useState<Record<string, string | boolean>>(() =>
    Object.fromEntries(
      fields.map((spec) => [
        spec.key,
        spec.kind === 'bool'
          ? Boolean(current[spec.key])
          : shown(current[spec.key]),
      ])
    )
  )
  const edit = useLoreEdit(entityId)
  const busy = busyOf(blocked, edit.isPending)
  const save = () =>
    edit.mutate({
      values: Object.fromEntries(
        fields
          .filter(
            (spec) =>
              parsed(spec, draft[spec.key]) !== (current[spec.key] ?? null)
          )
          .map((spec) => [spec.key, parsed(spec, draft[spec.key])])
      ),
    })
  const put = (key: string, value: string | boolean) =>
    setDraft((before) => ({ ...before, [key]: value }))
  return (
    <div data-surface={surface} className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        {fields.map((spec) => {
          if (spec.kind === 'enum')
            return (
              <MindPicker
                key={spec.key}
                label={words(spec.key)}
                value={String(draft[spec.key])}
                table={table(spec.values)}
                blocked={busy}
                onPick={(value) => put(spec.key, value)}
              />
            )
          if (spec.kind === 'bool')
            return (
              <label key={spec.key} className='flex min-w-0 items-center gap-2'>
                <Switch
                  checked={Boolean(draft[spec.key])}
                  disabled={busy !== null}
                  aria-label={words(spec.key)}
                  onCheckedChange={(next) => put(spec.key, next)}
                />
                <Text as='span'>{words(spec.key)}</Text>
              </label>
            )
          return (
            <div key={spec.key} className='flex min-w-0 flex-col gap-1'>
              <Label>{words(spec.key)}</Label>
              <Input
                type={spec.kind === 'number' ? 'number' : 'text'}
                min={spec.kind === 'number' ? spec.min : undefined}
                max={spec.kind === 'number' ? spec.max : undefined}
                value={String(draft[spec.key])}
                aria-label={words(spec.key)}
                onChange={(event) => put(spec.key, event.target.value)}
              />
            </div>
          )
        })}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={save}
        >
          <Save />
          Set it so
        </Button>
        {locked.length > 0 && (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => edit.mutate({ values: {}, release: [...locked] })}
          >
            <Unlock />
            Let the world decide again
          </Button>
        )}
        {locked.map((key) => (
          <Badge key={key} variant='outline'>{`held: ${words(key)}`}</Badge>
        ))}
      </div>
    </div>
  )
}

export function DictField({
  entityId,
  spec,
  blocked,
  suggestions = [],
}: {
  entityId: number
  spec: DictSpec
  blocked: string | null
  suggestions?: readonly string[]
}) {
  const [rows, setRows] = useState<Array<[string, string]>>(() =>
    Object.entries(spec.value).map(([key, value]) => [key, String(value)])
  )
  const [fresh, setFresh] = useState('')
  const edit = useLoreEdit(entityId)
  const busy = busyOf(blocked, edit.isPending)
  const save = (next: Array<[string, string]>) =>
    edit.mutate({
      values: {
        [spec.key]: Object.fromEntries(
          next.map(([key, value]) => [
            key,
            Number.isNaN(Number(value)) ? value : Math.round(Number(value)),
          ])
        ),
      },
    })
  return (
    <div data-surface='LoreDictField' className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{spec.label}</Label>
      <ul className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'>
        {rows.map(([key, value], index) => (
          <li key={key} className='flex min-w-0 items-center gap-2'>
            <Text as='span' className='min-w-24'>
              {words(key)}
            </Text>
            <Input
              value={value}
              aria-label={words(key)}
              onChange={(event) =>
                setRows((before) =>
                  before.map((row, at) =>
                    at === index ? [row[0], event.target.value] : row
                  )
                )
              }
            />
            <Button
              size='icon'
              variant='ghost'
              aria-label={`Remove ${words(key)}`}
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => {
                const next = rows.filter((_, at) => at !== index)
                setRows(next)
                save(next)
              }}
            >
              <Trash2 />
            </Button>
          </li>
        ))}
      </ul>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        {suggestions.length > 0 ? (
          <MindPicker
            label='Add'
            value={fresh}
            table={table(
              suggestions.filter((item) => !rows.some(([key]) => key === item))
            )}
            blocked={busy}
            placeholder='Choose'
            onPick={setFresh}
          />
        ) : (
          <div className='flex min-w-0 flex-col gap-1'>
            <Label>Add</Label>
            <Input
              value={fresh}
              aria-label='New entry'
              onChange={(event) => setFresh(event.target.value)}
            />
          </div>
        )}
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || fresh === ''}
          disabledReason={
            busy ?? (fresh === '' ? 'Name the entry first' : undefined)
          }
          onClick={() => {
            setRows((before) => [...before, [fresh, '0']])
            setFresh('')
          }}
        >
          <Plus />
          Add
        </Button>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save(rows)}
        >
          <Save />
          Set it so
        </Button>
      </div>
    </div>
  )
}
