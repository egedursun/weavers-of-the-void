import { type ReactNode, useId, useState } from 'react'
import {
  Archive,
  ArchiveRestore,
  BookOpen,
  Check,
  Copy,
  Crown,
  FileUp,
  ImageUp,
  Info,
  LoaderCircle,
  type LucideIcon,
  NotebookPen,
  PenLine,
  Power,
  Star,
  Trash2,
  UsersRound,
  X,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatCompact, formatInteger } from '@/lib/format'
import { formatBytes } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { OrnateFrame } from '@/components/ui/ornate'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { MiniStat } from '@/components/domain'
import { Muted, SectionTitle, Text } from '@/components/typography'
import { UniverseCover } from './UniverseCrest'
import { useArchiveUniverse, useCloseUniverse, useEditUniverse } from './api'
import { type UniverseSummary } from './types'
import { ORIGIN_LOOK, crestTone } from './universeLook'
import {
  type UniverseAct,
  NAME_MAX,
  ageLine,
  archivedReason,
  born,
  busyReason,
  nameProblem,
  timeLine,
} from './universeModel'

type UniverseCardProps = {
  universe: UniverseSummary
  opening: boolean
  onOpen: () => void
  onAct: (act: UniverseAct) => void
}

function CardAction({
  icon: Icon,
  label,
  onClick,
  reason = null,
  tone = 'default',
  pressed,
}: {
  icon: LucideIcon
  label: string
  onClick: () => void
  reason?: string | null
  tone?: 'default' | 'danger'
  pressed?: boolean
}) {
  const button = (
    <Button
      type='button'
      variant='ghost'
      size='icon-sm'
      aria-label={label}
      aria-pressed={pressed}
      disabled={reason !== null}
      disabledReason={reason ?? undefined}
      onClick={onClick}
      className={cn(
        tone === 'danger' && 'text-destructive',
        pressed && 'text-primary'
      )}
    >
      <Icon className={cn(pressed && 'fill-primary')} />
    </Button>
  )
  if (reason !== null) return button
  return (
    <Tooltip>
      <TooltipTrigger asChild>{button}</TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}

function InlineName({
  universe,
  reason,
}: {
  universe: UniverseSummary
  reason: string | null
}) {
  const headingId = useId()
  const [draft, setDraft] = useState<string | null>(null)
  const edit = useEditUniverse()
  const problem = draft === null ? null : nameProblem(draft)
  const save = () => {
    if (draft === null || problem !== null) return
    const name = draft.trim()
    if (name === universe.name) {
      setDraft(null)
      return
    }
    edit.mutate(
      { id: universe.id, edit: { name } },
      {
        onSuccess: () => {
          setDraft(null)
          toast.success(`Renamed to ${name}`)
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }
  if (draft === null)
    return (
      <div className='flex min-w-0 items-start gap-1'>
        <SectionTitle
          id={headingId}
          level={3}
          truncate={2}
          className='min-w-0 flex-1 text-gilded'
        >
          {universe.name}
        </SectionTitle>
        <CardAction
          icon={PenLine}
          label={`Rename ${universe.name}`}
          reason={reason}
          onClick={() => setDraft(universe.name)}
        />
      </div>
    )
  return (
    <form
      className='flex min-w-0 flex-col gap-1'
      onSubmit={(event) => {
        event.preventDefault()
        save()
      }}
    >
      <div className='flex min-w-0 items-center gap-1'>
        <Input
          autoFocus
          value={draft}
          maxLength={NAME_MAX}
          aria-label={`New name for ${universe.name}`}
          aria-invalid={problem !== null || undefined}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Escape') setDraft(null)
          }}
        />
        <Button
          type='submit'
          size='icon-sm'
          aria-label='Save the name'
          disabled={problem !== null || edit.isPending}
          disabledReason={problem ?? 'The name is being saved.'}
        >
          {edit.isPending ? (
            <LoaderCircle className='animate-spin motion-reduce:animate-none' />
          ) : (
            <Check />
          )}
        </Button>
        <Button
          type='button'
          variant='ghost'
          size='icon-sm'
          aria-label='Keep the old name'
          onClick={() => setDraft(null)}
        >
          <X />
        </Button>
      </div>
      {problem && (
        <Text variant='caption' tone='destructive'>
          {problem}
        </Text>
      )}
    </form>
  )
}

function Ribbon({ children }: { children: ReactNode }) {
  return (
    <div className='pointer-events-none absolute inset-x-0 top-0 flex min-w-0 flex-wrap items-start justify-between gap-1 p-2'>
      {children}
    </div>
  )
}

export function UniverseCard({
  universe,
  opening,
  onOpen,
  onAct,
}: UniverseCardProps) {
  const edit = useEditUniverse()
  const archive = useArchiveUniverse()
  const close = useCloseUniverse()
  const origin = ORIGIN_LOOK[universe.origin]
  const OriginIcon = origin.icon
  const archived = universe.status === 'archived'
  const alive = born(universe)
  const busy = busyReason(universe)
  const shelved = archivedReason(universe)
  const togglePin = () =>
    edit.mutate(
      { id: universe.id, edit: { pinned: !universe.pinned } },
      {
        onSuccess: () =>
          toast.success(
            universe.pinned
              ? `${universe.name} left the pinned row`
              : `${universe.name} is pinned to the front of the hall`
          ),
        onError: (error) => toast.error(error.message),
      }
    )
  const toggleArchive = () =>
    archive.mutate(
      { id: universe.id, archive: !archived },
      {
        onSuccess: () =>
          toast.success(
            archived
              ? `${universe.name} is back on the shelf`
              : `${universe.name} is archived`
          ),
        onError: (error) => toast.error(error.message),
      }
    )
  const putAway = () =>
    close.mutate(universe.id, {
      onSuccess: () => toast.success(`${universe.name} is closed`),
      onError: (error) => toast.error(error.message),
    })
  return (
    <OrnateFrame
      bayClassName='h-full'
      data-domain='universe-book'
      data-status={universe.status}
      frame='card'
      crest={universe.pinned}
      tone={archived ? 'muted' : crestTone(universe.name)}
      aria-label={universe.name}
      role='group'
      className={cn(
        '@container/library flex h-full min-w-0 flex-col gap-3 p-3 transition-opacity',
        archived && 'opacity-80'
      )}
    >
      <div className='relative aspect-video min-w-0 overflow-hidden rounded-md surface-well'>
        <UniverseCover universe={universe} />
        <Ribbon>
          <Badge variant='secondary' size='sm'>
            <OriginIcon aria-hidden='true' />
            {origin.label}
          </Badge>
          <span className='pointer-events-auto flex items-center gap-1'>
            {universe.is_open && (
              <Badge variant='success' size='sm'>
                <Power aria-hidden='true' />
                Open now
              </Badge>
            )}
            {universe.running_jobs.length > 0 && (
              <Badge variant='warning' size='sm'>
                <LoaderCircle
                  aria-hidden='true'
                  className='animate-spin motion-reduce:animate-none'
                />
                At work
              </Badge>
            )}
          </span>
        </Ribbon>
        {archived && (
          <span className='absolute inset-x-0 bottom-0 flex justify-center p-2'>
            <Badge variant='outline'>
              <Archive aria-hidden='true' />
              Archived
            </Badge>
          </span>
        )}
      </div>
      <div className='flex min-w-0 items-start gap-1'>
        <div className='min-w-0 flex-1'>
          <InlineName universe={universe} reason={shelved} />
        </div>
        <CardAction
          icon={Star}
          label={
            universe.pinned ? `Unpin ${universe.name}` : `Pin ${universe.name}`
          }
          pressed={universe.pinned}
          reason={
            shelved ?? (edit.isPending ? 'The pin is being saved.' : null)
          }
          onClick={togglePin}
        />
      </div>
      <Muted variant='caption' truncate={3}>
        {universe.summary ||
          'No summary yet: it is written when the universe is born.'}
      </Muted>
      <div className='grid min-w-0 grid-cols-1 gap-2 @2xs/library:grid-cols-2'>
        <div className='min-w-0 @2xs/library:col-span-2'>
          <MiniStat
            icon={BookOpen}
            label='Time'
            value={timeLine(universe)}
            hint={timeLine(universe)}
            tone='gold'
          />
        </div>
        <MiniStat
          icon={UsersRound}
          label='Population'
          value={alive ? formatCompact(universe.population) : 'None yet'}
          hint={
            alive ? `${formatInteger(universe.population)} living` : undefined
          }
          tone='info'
        />
        <MiniStat
          icon={Crown}
          label='Sons'
          value={alive ? formatInteger(universe.sons) : 'None yet'}
          tone='verdigris'
        />
      </div>
      {universe.tags.length > 0 && (
        <ul aria-label='Tags' className='flex min-w-0 flex-wrap gap-1'>
          {universe.tags.slice(0, 6).map((tag) => (
            <li key={tag}>
              <Badge variant='outline' size='sm'>
                {tag}
              </Badge>
            </li>
          ))}
          {universe.tags.length > 6 && (
            <li>
              <Badge variant='outline' size='sm'>
                {`+${formatInteger(universe.tags.length - 6)}`}
              </Badge>
            </li>
          )}
        </ul>
      )}
      <Muted variant='caption'>
        {`${ageLine(universe)} · ${formatBytes(universe.size_bytes)}`}
      </Muted>
      <div className='mt-auto flex min-w-0 flex-col gap-2 border-t border-gild/30 pt-3'>
        <Button
          type='button'
          onClick={onOpen}
          disabled={archived || opening}
          disabledReason={
            archived
              ? 'This universe is archived. Restore it to open it.'
              : 'The universe is being opened.'
          }
          aria-label={`Open ${universe.name}`}
        >
          {opening ? (
            <LoaderCircle className='animate-spin motion-reduce:animate-none' />
          ) : (
            <BookOpen />
          )}
          {opening ? 'Opening' : 'Open'}
        </Button>
        <div
          role='toolbar'
          aria-label={`Acts on ${universe.name}`}
          className='flex min-w-0 flex-wrap items-center justify-center gap-0.5'
        >
          <CardAction
            icon={Info}
            label={`Every fact of ${universe.name}`}
            onClick={() => onAct('details')}
          />
          <CardAction
            icon={NotebookPen}
            label='Notes and tags'
            reason={shelved}
            onClick={() => onAct('notes')}
          />
          <CardAction
            icon={ImageUp}
            label='Set the cover'
            reason={shelved}
            onClick={() => onAct('cover')}
          />
          <CardAction
            icon={Copy}
            label='Duplicate'
            reason={shelved}
            onClick={() => onAct('duplicate')}
          />
          <CardAction
            icon={FileUp}
            label='Export as a file'
            reason={shelved}
            onClick={() => onAct('export')}
          />
          {universe.is_open && (
            <CardAction
              icon={Power}
              label='Close it'
              reason={busy ?? (close.isPending ? 'It is being closed.' : null)}
              onClick={putAway}
            />
          )}
          <CardAction
            icon={archived ? ArchiveRestore : Archive}
            label={archived ? 'Restore to the shelf' : 'Archive'}
            reason={
              (archived ? null : busy) ??
              (archive.isPending ? 'The archive is being changed.' : null)
            }
            onClick={toggleArchive}
          />
          <CardAction
            icon={Trash2}
            label='Delete'
            tone='danger'
            reason={busy}
            onClick={() => onAct('delete')}
          />
        </div>
      </div>
    </OrnateFrame>
  )
}
