import { type ReactNode, useState } from 'react'
import {
  Copy,
  Crown,
  HardDrive,
  Hourglass,
  Info,
  LoaderCircle,
  NotebookPen,
  Power,
  Star,
  Trash2,
  Users,
  Wrench,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatDateTime, formatInteger } from '@/lib/format'
import { formatBytes } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Dialog, DialogContent, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  ConfirmDialog,
  EmptyState,
  FormRow,
  KeyValueList,
  LoadingBlock,
  MiniStat,
  Paged,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { type ActDialogProps, ActHeader } from './ActHeader'
import { CoverDialog } from './CoverDialog'
import { ExportDialog } from './ExportDialog'
import { UniverseCover } from './UniverseCrest'
import {
  useDeleteUniverse,
  useDuplicateUniverse,
  useEditUniverse,
  useUniverse,
} from './api'
import { type UniverseSummary } from './types'
import { EVENT_LOOK, ORIGIN_LOOK, STATUS_LOOK } from './universeLook'
import {
  type UniverseAct,
  NAME_MAX,
  NOTES_MAX,
  born,
  busyReason,
  cleanTags,
  nameProblem,
  timeLine,
} from './universeModel'

function NotesDialog({ universe, onClose }: ActDialogProps) {
  const [notes, setNotes] = useState(universe.notes)
  const [summary, setSummary] = useState(universe.summary)
  const [tags, setTags] = useState(universe.tags.join(', '))
  const edit = useEditUniverse()
  const save = () =>
    edit.mutate(
      {
        id: universe.id,
        edit: {
          summary: summary.trim(),
          notes: notes.trim(),
          tags: cleanTags(tags),
        },
      },
      {
        onSuccess: () => {
          toast.success(`The notes of ${universe.name} are kept`)
          onClose()
        },
        onError: (error) => toast.error(error.message),
      }
    )
  return (
    <>
      <ActHeader
        icon={NotebookPen}
        title={`Summary, notes and tags of ${universe.name}`}
      >
        These stay in the library and never reach the universe itself.
      </ActHeader>
      <FormRow
        label='Summary'
        description='Shown on the book. Left empty, the library writes one from the seed.'
      >
        {(id) => (
          <Textarea
            id={id}
            value={summary}
            maxLength={NOTES_MAX}
            onChange={(event) => setSummary(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Notes'>
        {(id) => (
          <Textarea
            id={id}
            value={notes}
            maxLength={NOTES_MAX}
            onChange={(event) => setNotes(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Tags' description='Separate tags with commas.'>
        {(id) => (
          <Input
            id={id}
            value={tags}
            onChange={(event) => setTags(event.target.value)}
          />
        )}
      </FormRow>
      <DialogFooter>
        <Button type='button' variant='outline' onClick={onClose}>
          Cancel
        </Button>
        <Button
          type='button'
          disabled={edit.isPending}
          disabledReason='The notes are being saved.'
          onClick={save}
        >
          <NotebookPen />
          Save the notes
        </Button>
      </DialogFooter>
    </>
  )
}

function DuplicateDialog({ universe, onClose }: ActDialogProps) {
  const [name, setName] = useState(`${universe.name} (copy)`)
  const duplicate = useDuplicateUniverse()
  const problem = nameProblem(name)
  const save = () => {
    if (problem !== null) return
    duplicate.mutate(
      { id: universe.id, name: name.trim() },
      {
        onSuccess: (copy) => {
          toast.success(`${copy.name} stands on the shelf`)
          onClose()
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }
  return (
    <>
      <ActHeader icon={Copy} title={`Duplicate ${universe.name}`}>
        A full copy of the universe as it stands now, with every record and
        image, becomes a new book. The two never touch again.
      </ActHeader>
      <FormRow label='Name of the copy'>
        {(id) => (
          <div className='flex w-full min-w-0 flex-col gap-1'>
            <Input
              id={id}
              value={name}
              maxLength={NAME_MAX}
              aria-invalid={problem !== null || undefined}
              onChange={(event) => setName(event.target.value)}
            />
            {problem && (
              <Text variant='caption' tone='destructive'>
                {problem}
              </Text>
            )}
          </div>
        )}
      </FormRow>
      <Muted variant='caption'>
        {`About ${formatBytes(universe.size_bytes)} is copied.`}
      </Muted>
      <DialogFooter>
        <Button
          type='button'
          variant='outline'
          disabled={duplicate.isPending}
          disabledReason='The copy is being made.'
          onClick={onClose}
        >
          Cancel
        </Button>
        <Button
          type='button'
          disabled={problem !== null || duplicate.isPending}
          disabledReason={problem ?? 'The copy is being made.'}
          onClick={save}
        >
          {duplicate.isPending ? (
            <LoaderCircle className='animate-spin motion-reduce:animate-none' />
          ) : (
            <Copy />
          )}
          {duplicate.isPending ? 'Copying' : 'Duplicate'}
        </Button>
      </DialogFooter>
    </>
  )
}

const SOURCE_ID = /^[a-z0-9]{12}$/

function OriginLine({ universe }: { universe: UniverseSummary }) {
  const note = universe.origin_note
  const sourceId =
    universe.origin === 'duplicated' && SOURCE_ID.test(note) ? note : null
  const source = useUniverse(sourceId)
  const look = ORIGIN_LOOK[universe.origin]
  if (sourceId !== null)
    return (
      <>
        {source.data
          ? `Copied from ${source.data.name}`
          : source.isPending
            ? 'Copied from another universe'
            : 'Copied from a universe no longer on the shelf'}
      </>
    )
  if (universe.origin === 'imported' && note)
    return <>{`Brought in from ${note}`}</>
  return <>{note ? `${look.phrase}: ${note}` : look.phrase}</>
}

function DetailsDialog({ universe, onClose }: ActDialogProps) {
  const detail = useUniverse(universe.id)
  const facts = detail.data ?? universe
  const status = STATUS_LOOK[facts.status]
  const origin = ORIGIN_LOOK[facts.origin]
  const StatusIcon = status.icon
  const OriginIcon = origin.icon
  const events = detail.data?.events ?? []
  const working = busyReason(facts)
  const living = born(facts)
  return (
    <>
      <ActHeader icon={Info} title={facts.name}>
        Every fact the library keeps about this universe.
      </ActHeader>
      <div className='grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-5'>
        <div className='aspect-video min-w-0 overflow-hidden rounded-md surface-framed sm:col-span-2 sm:aspect-square'>
          <UniverseCover universe={facts} />
        </div>
        <div className='flex min-w-0 flex-col gap-3 sm:col-span-3'>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Badge variant='outline' size='sm'>
              <StatusIcon />
              {status.label}
            </Badge>
            <Badge variant='outline' size='sm'>
              <OriginIcon />
              {origin.label}
            </Badge>
            {facts.pinned && (
              <Badge variant='secondary' size='sm'>
                <Star className='fill-primary text-primary' />
                Pinned
              </Badge>
            )}
            {facts.is_open && (
              <Badge variant='success' size='sm'>
                <Power />
                Open now
              </Badge>
            )}
            {working && (
              <Badge variant='warning' size='sm'>
                <LoaderCircle className='animate-spin motion-reduce:animate-none' />
                At work
              </Badge>
            )}
          </div>
          <Text className='italic'>
            {facts.summary ||
              'No summary yet: it is written when the universe is born.'}
          </Text>
          <Muted variant='caption'>
            <OriginLine universe={facts} />
          </Muted>
          {working && <Muted variant='caption'>{working}</Muted>}
        </div>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <MiniStat
          icon={Hourglass}
          label='Time'
          value={timeLine(facts)}
          tone='gold'
        />
        <MiniStat
          icon={Users}
          label='Population'
          value={living ? formatInteger(facts.population) : 'None yet'}
          tone='info'
        />
        <MiniStat
          icon={Crown}
          label='Sons'
          value={living ? formatInteger(facts.sons) : 'None yet'}
          tone='gold'
        />
        <MiniStat
          icon={HardDrive}
          label='On disk'
          value={formatBytes(facts.size_bytes)}
          tone='muted'
        />
      </div>
      <div className='flex min-w-0 flex-col gap-4'>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='gilded'>On the shelf</Label>
          <KeyValueList
            items={[
              { label: 'Created', value: formatDateTime(facts.created_at) },
              {
                label: 'Last opened',
                value: facts.opened_at
                  ? formatDateTime(facts.opened_at)
                  : 'Never opened',
              },
              {
                label: 'Last changed',
                value: formatDateTime(facts.updated_at),
              },
              {
                label: 'Cover',
                value: facts.cover_path
                  ? 'An image of your choosing'
                  : 'The crest of its name',
              },
            ]}
          />
        </div>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='gilded'>Notes and tags</Label>
          <div className='flex min-w-0 flex-col gap-2 rounded-md surface-well p-3'>
            <Text variant='caption' className='whitespace-pre-wrap'>
              {facts.notes || 'No notes yet.'}
            </Text>
            {facts.tags.length === 0 ? (
              <Muted variant='caption'>No tags.</Muted>
            ) : (
              <TagList tags={facts.tags} />
            )}
          </div>
        </div>
      </div>
      <Collapsible className='flex min-w-0 flex-col gap-2'>
        <CollapsibleTrigger asChild>
          <Button
            type='button'
            variant='ghost'
            size='sm'
            className='self-start'
          >
            <Wrench />
            For the keeper
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <KeyValueList
            items={[
              {
                label: 'Universe id',
                value: <Text className='font-mono'>{facts.id}</Text>,
              },
              {
                label: 'Schema revision',
                value: facts.schema_revision ? (
                  <Text className='font-mono'>{facts.schema_revision}</Text>
                ) : (
                  'Not yet recorded'
                ),
              },
              {
                label: 'Made with app version',
                value: facts.app_version || 'Unknown',
              },
              {
                label: 'Media folder',
                value: facts.media_prefix ? (
                  <Text as='span' className='font-mono'>
                    {facts.media_prefix}
                  </Text>
                ) : (
                  'The shared root, kept from before the library'
                ),
              },
            ]}
          />
        </CollapsibleContent>
      </Collapsible>
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='gilded'>Recent acts</Label>
        {detail.isPending ? (
          <LoadingBlock label='Reading the acts' />
        ) : events.length === 0 ? (
          <EmptyState
            size='inline'
            icon={Info}
            title='No acts yet'
            description='Opening, renaming, exporting and the rest are kept here.'
          />
        ) : (
          <ol className='flex min-w-0 flex-col gap-1'>
            <Paged items={events} as='li'>
              {(event) => {
                const look = EVENT_LOOK[event.kind]
                const Icon = look.icon
                return (
                  <li
                    key={event.id}
                    className='flex min-w-0 items-center gap-2 rounded-md surface-sheen px-2 py-1.5'
                  >
                    <Icon
                      aria-hidden='true'
                      className='size-icon-sm shrink-0 text-primary'
                    />
                    <Text
                      as='span'
                      variant='caption'
                      weight='medium'
                      className='min-w-0 flex-1'
                    >
                      {event.detail
                        ? `${look.label}: ${event.detail}`
                        : look.label}
                    </Text>
                    <Muted as='span' variant='caption'>
                      {formatDateTime(event.at)}
                    </Muted>
                  </li>
                )
              }}
            </Paged>
          </ol>
        )}
      </div>
      <DialogFooter>
        <Button type='button' variant='outline' onClick={onClose}>
          Close
        </Button>
      </DialogFooter>
    </>
  )
}

export function DeleteUniverseDialog({
  universe,
  onClose,
}: {
  universe: UniverseSummary | null
  onClose: () => void
}) {
  const remove = useDeleteUniverse()
  const busy = universe ? busyReason(universe) : null
  return (
    <ConfirmDialog
      open={universe !== null}
      onOpenChange={(open) => {
        if (!open && !remove.isPending) onClose()
      }}
      destructive
      title={universe ? `Delete ${universe.name}?` : 'Delete the universe?'}
      desc={
        <div className='flex flex-col gap-2'>
          <Text>
            {universe
              ? `${universe.name} leaves the shelf and goes to the trash with every record and image it holds.`
              : ''}
          </Text>
          <Muted>
            You can bring it back from the trash until it is purged.
          </Muted>
          {busy && <Text tone='warning'>{busy}</Text>}
        </div>
      }
      confirmText={
        <>
          <Trash2 />
          {universe ? `Delete ${universe.name}` : 'Delete'}
        </>
      }
      disabled={busy !== null}
      isLoading={remove.isPending}
      handleConfirm={() => {
        if (!universe) return
        remove.mutate(universe.id, {
          onSuccess: () => {
            toast.success(`${universe.name} is in the trash`)
            onClose()
          },
          onError: (error) => toast.error(error.message),
        })
      }}
    />
  )
}

const ACT_DIALOG: Record<
  Exclude<UniverseAct, 'delete'>,
  (props: ActDialogProps) => ReactNode
> = {
  notes: NotesDialog,
  cover: CoverDialog,
  duplicate: DuplicateDialog,
  export: ExportDialog,
  details: DetailsDialog,
}

export function UniverseActDialog({
  act,
  universe,
  onClose,
}: {
  act: Exclude<UniverseAct, 'delete'> | null
  universe: UniverseSummary | null
  onClose: () => void
}) {
  const Body = act ? ACT_DIALOG[act] : null
  return (
    <Dialog
      open={Body !== null && universe !== null}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <DialogContent className='sm:max-w-2xl'>
        {Body && universe && (
          <Body
            key={`${act ?? ''}-${universe.id}`}
            universe={universe}
            onClose={onClose}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}

const SHOWN_TAGS = 8

function TagList({ tags }: { tags: readonly string[] }) {
  const shown = useShowMore(tags, SHOWN_TAGS)
  return (
    <span className='flex min-w-0 flex-col gap-1'>
      <span className='flex min-w-0 flex-wrap gap-1'>
        {shown.visible.map((tag) => (
          <Badge key={tag} variant='outline' size='sm'>
            {tag}
          </Badge>
        ))}
      </span>
      <ShowMore state={shown} noun={['tag', 'tags']} />
    </span>
  )
}
