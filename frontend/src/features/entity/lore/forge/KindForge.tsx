import { useState } from 'react'
import { Pencil, Plus, Shapes, Trash2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState, Paged, FieldTile } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { AdjustBlock, ChoicePicker, NamedChip, ShiftChips } from '../LoreFields'
import { busyOf, lookup } from '../model'
import { kindKeys, useCustomKinds } from './kindApi'
import {
  KIND_CATALOG,
  type KindParamField,
  type KindParams,
  paramsOf,
} from './kindModel'

type Catalog = components['schemas']['CustomCatalog']
type CustomKind = components['schemas']['CustomKindView']

function ParamInput({
  field,
  params,
  put,
}: {
  field: KindParamField
  params: KindParams
  put: (next: KindParams) => void
}) {
  const value = params[field.key]
  if (field.kind === 'enum')
    return (
      <ChoicePicker
        label={field.label}
        value={typeof value === 'string' ? value : ''}
        table={field.table}
        blocked={null}
        placeholder='As the base'
        onPick={(next) => put({ ...params, [field.key]: next })}
      />
    )
  if (field.kind === 'number')
    return (
      <FieldTile label={`${field.label} (${field.min}–${field.max})`}>
        <Input
          type='number'
          min={field.min}
          max={field.max}
          aria-label={field.label}
          value={typeof value === 'number' ? String(value) : ''}
          placeholder='As the base'
          onChange={(event) => {
            const raw = event.target.value
            const next = { ...params }
            if (raw === '') delete next[field.key]
            else next[field.key] = Math.round(Number(raw) || 0)
            put(next)
          }}
        />
      </FieldTile>
    )
  const table =
    value && typeof value === 'object' && !Array.isArray(value)
      ? (value as Record<string, number>)
      : {}
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <FieldTile label={field.label}>
        <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
          {Object.entries(field.table).map(([key, spec]) => (
            <div key={key} className='flex min-w-0 flex-col gap-1'>
              <Muted variant='caption'>{spec.label}</Muted>
              <Input
                type='number'
                aria-label={`${field.label}: ${spec.label}`}
                value={key in table ? String(table[key]) : ''}
                onChange={(event) => {
                  const raw = event.target.value
                  const next = { ...table }
                  if (raw === '') delete next[key]
                  else next[key] = Math.round(Number(raw) || 0)
                  put({ ...params, [field.key]: next })
                }}
              />
            </div>
          ))}
        </div>
      </FieldTile>
    </div>
  )
}

function KindEditor({
  catalog,
  kind,
  blocked,
  onDone,
}: {
  catalog: Catalog
  kind: CustomKind | null
  blocked: string | null
  onDone: () => void
}) {
  const spec = KIND_CATALOG[catalog]
  const [name, setName] = useState(kind?.name ?? '')
  const [base, setBase] = useState(kind?.base ?? '')
  const [params, setParams] = useState<KindParams>(paramsOf(kind?.params))
  const save = useGodAction({
    run: () =>
      kind
        ? unwrap(
            api.POST('/api/actions/kind:edit', {
              body: {
                kind_id: kind.id,
                values: { name, base, params } as unknown as Record<
                  string,
                  never
                >,
              },
            })
          )
        : unwrap(
            api.POST('/api/actions/kind:create', {
              body: {
                catalog,
                base,
                name,
                description: '',
                params: params as Record<string, never>,
              },
            })
          ),
    invalidate: [kindKeys.list(catalog)],
    onDone,
  })
  const busy = busyOf(
    blocked ??
      (name.trim() ? null : 'Name it first') ??
      (base ? null : `Choose the ${spec.baseLabel.toLowerCase()}`),
    save.isPending
  )
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md p-3 sealed-well'>
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
        <FieldTile label='Name'>
          <Input
            aria-label='Name of the kind'
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </FieldTile>
        <ChoicePicker
          label={spec.baseLabel}
          value={base}
          table={spec.bases}
          blocked={null}
          placeholder='Choose'
          onPick={setBase}
        />
        {spec.params.map((field) => (
          <ParamInput
            key={field.key}
            field={field}
            params={params}
            put={setParams}
          />
        ))}
      </div>
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => save.mutate()}
      >
        {kind ? <Pencil /> : <Plus />}
        {kind ? 'Reshape it' : `Name this ${spec.noun}`}
      </Button>
    </div>
  )
}

export function KindForge({ catalog }: { catalog: Catalog }) {
  const spec = KIND_CATALOG[catalog]
  const kinds = useCustomKinds(catalog)
  const { reason } = useGodGate()
  const blocked = reason()
  const [editing, setEditing] = useState<number | 'new' | null>(null)
  const remove = useGodAction<number>({
    run: (kindId) =>
      unwrap(
        api.POST('/api/actions/kind:delete', { body: { kind_id: kindId } })
      ),
    invalidate: [kindKeys.list(catalog)],
  })
  const busy = busyOf(blocked, remove.isPending)
  const rows = kinds.data?.kinds ?? []
  return (
    <AdjustBlock title={spec.title} icon={Shapes}>
      <div data-surface='KindForge' className='flex min-w-0 flex-col gap-3'>
        <Muted variant='caption'>{spec.note}</Muted>
        {rows.length === 0 && (
          <EmptyState
            icon={Shapes}
            title={`No ${spec.noun}s of your own yet`}
            description={`Name a new ${spec.noun} built on one the world already knows; it acts as its base with your changes.`}
          />
        )}
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={rows} as='li'>
            {(row) => (
              <li key={row.id} className='flex min-w-0 flex-col gap-2'>
                <div className='flex min-w-0 flex-wrap items-center gap-2'>
                  <Text weight='semibold'>{row.name}</Text>
                  <NamedChip spec={lookup(spec.bases, row.base)}>
                    {`on ${lookup(spec.bases, row.base).label.toLowerCase()}`}
                  </NamedChip>
                  <ShiftChips
                    entries={spec.summary(paramsOf(row.params))}
                    table={spec.summaryTable}
                    empty='As its base'
                  />
                  <Button
                    size='icon'
                    variant='ghost'
                    aria-label={`Reshape ${row.name}`}
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() =>
                      setEditing(editing === row.id ? null : row.id)
                    }
                  >
                    <Pencil />
                  </Button>
                  <Button
                    size='icon'
                    variant='ghost'
                    aria-label={`Unmake ${row.name}`}
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => remove.mutate(row.id)}
                  >
                    <Trash2 />
                  </Button>
                </div>
                {editing === row.id && (
                  <KindEditor
                    catalog={catalog}
                    kind={row}
                    blocked={blocked}
                    onDone={() => setEditing(null)}
                  />
                )}
              </li>
            )}
          </Paged>
        </ul>
        {editing === 'new' ? (
          <KindEditor
            catalog={catalog}
            kind={null}
            blocked={blocked}
            onDone={() => setEditing(null)}
          />
        ) : (
          <Button
            size='sm'
            variant='outline'
            className='self-start'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => setEditing('new')}
          >
            <Plus />
            {`Name a new ${spec.noun}`}
          </Button>
        )}
      </div>
    </AdjustBlock>
  )
}
