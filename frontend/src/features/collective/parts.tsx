import { type ReactNode, useMemo } from 'react'
import { type LucideIcon, Trash2 } from 'lucide-react'
import { type ActProp } from '@/api/mutation'
import { Button } from '@/components/ui/button'
import { PagedList } from '@/components/domain'
import { type KpiTone } from '@/components/domain/KpiTile'
import { Label, Muted } from '@/components/typography'
import { RecordEditor, RecordRow } from '@/features/cosmography/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { useHistories } from '@/features/gatherings/api'
import { type Edit } from './model'

export type Field = Parameters<typeof RecordEditor>[0]['fields'][number]

export function Held({
  icon,
  tone,
  title,
  caption,
  removeLabel,
  editTitle,
  note,
  fields,
  locked,
  blocked,
  onEdit,
  onRemove,
  children,
  extra,
  act,
}: {
  icon: LucideIcon
  tone: KpiTone
  title: ReactNode
  caption: ReactNode
  removeLabel: string
  editTitle: string
  note: string
  fields: Field[]
  locked: string[]
  blocked: string | null
  onEdit: ((vars: Edit) => void) | null
  onRemove: () => void
  children?: ReactNode
  extra?: ReactNode
  act?: ActProp
}) {
  return (
    <RecordRow
      icon={icon}
      tone={tone}
      title={title}
      caption={caption}
      aside={
        <Button
          act={act}
          size='sm'
          variant='ghost'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={onRemove}
        >
          <Trash2 />
          {removeLabel}
        </Button>
      }
    >
      {extra && <div className='flex min-w-0 flex-wrap gap-2'>{extra}</div>}
      {children}
      {onEdit && fields.length > 0 && (
        <RecordEditor
          act={act}
          title={editTitle}
          note={note}
          fields={fields}
          locked={locked}
          busy={blocked}
          onSave={(values) => onEdit({ values, release: [] })}
          onRelease={(release) => onEdit({ values: {}, release })}
        />
      )}
    </RecordRow>
  )
}

export function Listed<T>({
  title,
  items,
  empty,
  noun,
  itemKey,
  children,
}: {
  title: string
  items: T[]
  empty: string
  noun: [string, string]
  itemKey: (item: T) => string | number
  children: (item: T) => ReactNode
}) {
  return (
    <>
      <Label variant='overline'>{`${title} (${items.length})`}</Label>
      {items.length === 0 ? (
        <Muted variant='caption'>{empty}</Muted>
      ) : (
        <PagedList
          items={items}
          initial={3}
          noun={noun}
          className='flex min-w-0 flex-col gap-2'
          itemKey={itemKey}
        >
          {children}
        </PagedList>
      )}
    </>
  )
}

export function EventPicker({
  nodeId,
  value,
  blocked,
  onPick,
}: {
  nodeId: number
  value: string
  blocked: string | null
  onPick: (value: string) => void
}) {
  const own = useHistories({ node_id: nodeId, limit: 50 })
  const table = useMemo(
    () =>
      Object.fromEntries(
        (own.data?.items ?? []).map((item) => [String(item.id), item.name])
      ),
    [own.data]
  )
  const empty = Object.keys(table).length === 0
  return (
    <MindPicker
      label='Event'
      value={value}
      table={table}
      blocked={
        blocked ??
        (own.isPending
          ? 'Reading the events'
          : empty
            ? 'No event has taken place here yet'
            : null)
      }
      placeholder='Choose an event'
      onPick={onPick}
    />
  )
}
