import { useMemo, useState } from 'react'
import {
  CalendarDays,
  ChevronDown,
  Clock,
  FileStack,
  Layers,
  NotebookPen,
  Search,
  Undo2,
  Users,
  X,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatDateTime, formatInteger } from '@/lib/format'
import { agree, plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ConfirmDialog,
  EmptyState,
  Medallion,
  MiniStat,
} from '@/components/domain'
import { MentionText } from '@/components/domain/MentionText'
import { Label, Muted, Text } from '@/components/typography'
import { NodeLink } from '@/features/feed/NodeLink'
import { type NodeIndex, useNodeIndex } from '@/features/feed/nodes'
import { useWorldState } from '@/features/overview/api'
import { useRuleValue } from '@/features/world-rules/api'
import {
  type LedgerEntryView,
  type LedgerQuery,
  type UndoResult,
  useEnumCatalogue,
  useLedger,
  useUndo,
} from './api'
import {
  ACTION_ICON,
  ACTOR,
  ACTOR_KINDS,
  type ActorKind,
  DEFAULT_ACTION_ICON,
  sentence,
} from './ledgerVisuals'
import { undoMessage } from './undoToast'

const EVERY_SON = 'every-son'
const PAGE_MAX_RULE = 'server.ledger_page_max'
const PAGE_SIZE_RULE = 'server.ledger_page_size'
const RETENTION_RULE = 'ledger.keep_epochs'
const PERCENT = 100

const dateTime = new Intl.DateTimeFormat('en-US', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

type EntryProps = {
  view: LedgerEntryView
  index: NodeIndex
  epochRunning: boolean
  result: UndoResult | undefined
  onUndone: (result: UndoResult) => void
}

function undoReason(view: LedgerEntryView, epochRunning: boolean) {
  if (epochRunning) return 'A page cannot be torn out while the epoch runs'
  if (view.change_count === 0)
    return 'Nothing on this page can be undone; it keeps only its story'
  return null
}

function LedgerEntry({
  view,
  index,
  epochRunning,
  result,
  onUndone,
}: EntryProps) {
  const { entry } = view
  const undo = useUndo()
  const [confirming, setConfirming] = useState(false)
  const dependents = view.dependents.length
  const conflicts = result?.conflicts ?? entry.conflicts
  const actor = ACTOR[entry.actor_kind]
  const Icon = ACTION_ICON[entry.action_kind] ?? DEFAULT_ACTION_ICON
  const blocked = undoReason(view, epochRunning)
  return (
    <li
      data-ledger-entry={entry.id}
      className={cn(
        'flex min-w-0 gap-3 rounded-xl border bg-background p-3',
        entry.undone && 'bg-muted/40'
      )}
    >
      <Medallion
        icon={Icon}
        tone={entry.undone ? 'muted' : actor.tone}
        size='sm'
      />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <div className='flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1'>
          <Text as='span' weight='semibold' className='min-w-0'>
            {entry.actor_node_id !== null ? (
              <NodeLink
                nodeId={entry.actor_node_id}
                index={index}
                fallback={entry.actor_name}
              />
            ) : (
              entry.actor_name
            )}
          </Text>
          <Text
            as='span'
            truncate
            className={cn(
              'min-w-0 flex-1 basis-40',
              entry.undone && 'line-through'
            )}
          >
            {sentence(view.label)}
          </Text>
          {entry.undone ? (
            <Badge size='sm' variant='secondary'>
              <Undo2 />
              {entry.undone_at
                ? `Undone ${formatDateTime(entry.undone_at)}`
                : 'Undone'}
            </Badge>
          ) : (
            <Button
              variant='outline'
              size='sm'
              disabled={blocked !== null || undo.isPending}
              disabledReason={blocked ?? 'Undoing'}
              onClick={() => setConfirming(true)}
            >
              <Undo2 />
              Undo
            </Button>
          )}
        </div>
        {entry.input_summary && (
          <Muted variant='caption' truncate={3}>
            <MentionText text={entry.input_summary} />
          </Muted>
        )}
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant='outline'>{`#${entry.id}`}</Badge>
          <Badge size='sm' variant='outline'>
            <actor.icon />
            {actor.label}
          </Badge>
          <Badge size='sm' variant='outline'>
            <Clock />
            {dateTime.format(new Date(entry.created_at))}
          </Badge>
          {view.change_count > 0 && (
            <Badge size='sm' variant='info'>
              <Layers />
              {plural(view.change_count, 'change')}
            </Badge>
          )}
        </div>
        {dependents > 0 && !entry.undone && (
          <Text variant='caption' tone='warning'>
            {`${dependents === 1 ? 'The next page' : `The next ${plural(dependents, 'page', 'pages')}`} touched what this one created: ${view.dependents.map((id) => `#${id}`).join(', ')}`}
          </Text>
        )}
        {(result || (entry.undone && conflicts.length > 0)) && (
          <div className='flex min-w-0 flex-col gap-1 rounded-lg border bg-card p-3'>
            <Text variant='caption' weight='medium'>
              {undoMessage(
                result?.applied?.length ?? entry.applied.length,
                conflicts.length
              )}
            </Text>
            {conflicts.map((conflict) => (
              <Text key={conflict} variant='caption' tone='warning'>
                {conflict}
              </Text>
            ))}
          </div>
        )}
        {view.rows.length > 0 && (
          <Collapsible>
            <CollapsibleTrigger asChild>
              <Button variant='ghost' size='sm' className='w-fit'>
                <ChevronDown />
                {`What changed · ${view.rows.length}`}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <ul className='flex min-w-0 flex-col gap-1 border-s ps-3 pt-1'>
                {view.rows.map((row, position) => (
                  <li key={`${row}-${position}`}>
                    <Muted variant='caption'>{row}</Muted>
                  </li>
                ))}
              </ul>
            </CollapsibleContent>
          </Collapsible>
        )}
      </div>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={`Undo page #${entry.id}?`}
        desc={
          dependents > 0
            ? `${dependents === 1 ? 'The next page depends' : `The next ${plural(dependents, 'page', 'pages')} depend`} on this one. Undoing it may leave conflicts, which are skipped and listed. Spent essence is refunded.`
            : 'Its changes are reverted and any essence it spent is refunded.'
        }
        confirmText={dependents > 0 ? 'Undo anyway' : 'Undo'}
        destructive
        isLoading={undo.isPending}
        handleConfirm={() =>
          undo.mutate(entry.id, {
            onSuccess: (undone) => {
              setConfirming(false)
              onUndone(undone)
              toast.success(
                undoMessage(
                  undone.applied?.length ?? 0,
                  undone.conflicts?.length ?? 0
                )
              )
            },
            onError: (error) => {
              setConfirming(false)
              toast.error(error.message)
            },
          })
        }
      />
    </li>
  )
}

export function ActionLedger() {
  const state = useWorldState()
  const index = useNodeIndex()
  const pageMax = useRuleValue(PAGE_MAX_RULE)
  const defaultPageSize = useRuleValue(PAGE_SIZE_RULE)
  const retention = useRuleValue(RETENTION_RULE)
  const [query, setQuery] = useState<LedgerQuery>({
    epoch: null,
    actorKind: null,
    actorId: null,
    limit: null,
  })
  const [search, setSearch] = useState('')
  const [results, setResults] = useState<Map<number, UndoResult>>(new Map())
  const ledger = useLedger(query)
  const entries = useMemo(() => ledger.data?.entries ?? [], [ledger.data])
  const epochs = ledger.data?.epochs ?? []
  const pageSize = query.limit ?? defaultPageSize
  const capped = pageMax !== null && entries.length >= pageMax
  const full = pageSize !== null && entries.length >= pageSize
  const enums = useEnumCatalogue()
  const actorKinds = enums.data?.actor_kinds ?? ACTOR_KINDS
  const sons = state.data?.sons ?? []
  const needle = search.trim().toLowerCase()
  const shown = needle
    ? entries.filter((view) =>
        [view.label, view.entry.actor_name, view.entry.input_summary ?? '']
          .join(' ')
          .toLowerCase()
          .includes(needle)
      )
    : entries
  const groups = useMemo(() => {
    const map = new Map<number, LedgerEntryView[]>()
    for (const view of shown)
      map.set(view.entry.epoch, [...(map.get(view.entry.epoch) ?? []), view])
    return [...map.entries()].sort((left, right) => right[0] - left[0])
  }, [shown])
  const totalPages = epochs.reduce((sum, item) => sum + item.entries, 0)
  const totalUndone = epochs.reduce((sum, item) => sum + item.undone, 0)
  const busiest = Math.max(1, ...epochs.map((item) => item.entries))
  const current = ledger.data?.current_epoch
  const thisEpoch = epochs.find((item) => item.epoch === current)?.entries ?? 0
  const filtered =
    query.epoch !== null || query.actorKind !== null || needle !== ''
  const patch = (next: Partial<LedgerQuery>) =>
    setQuery((value) => ({ ...value, ...next, limit: null }))
  const chooseActor = (kind: ActorKind | null) =>
    patch({ actorKind: kind, actorId: null })

  return (
    <div className='flex min-w-0 flex-col gap-5'>
      <Muted>
        Every action of the sons, the mortals, Fate and you is written here as a
        page. Tear out a page and its changes are undone; spent essence is
        refunded.
        {retention !== null &&
          ` Pages of the last ${plural(retention, 'epoch', 'epochs')} ${agree(retention, 'is', 'are')} kept.`}
      </Muted>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <MiniStat
          icon={FileStack}
          label='Pages kept'
          value={totalPages}
          tone='gold'
        />
        <MiniStat
          icon={CalendarDays}
          label='This epoch'
          value={thisEpoch}
          tone='verdigris'
        />
        <MiniStat
          icon={Undo2}
          label='Torn out'
          value={totalUndone}
          tone={totalUndone > 0 ? 'warning' : 'muted'}
        />
        <MiniStat
          icon={Layers}
          label='Epochs kept'
          value={epochs.length}
          tone='info'
          hint={
            retention !== null
              ? `The ledger keeps ${plural(retention, 'epoch', 'epochs')}`
              : undefined
          }
        />
      </div>
      {epochs.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Epochs</Label>
          <ul className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-7'>
            <li className='min-w-0'>
              <Button
                variant='outline'
                size='tile'
                aria-pressed={query.epoch === null}
                onClick={() => patch({ epoch: null })}
                className={cn(
                  'flex-col items-stretch',
                  query.epoch === null && 'border-primary/50 bg-primary/10'
                )}
              >
                <Text as='span' weight='semibold'>
                  All epochs
                </Text>
                <Muted as='span' variant='caption'>
                  {plural(totalPages, 'page')}
                </Muted>
                <Progress size='sm' value={PERCENT} aria-label='All pages' />
              </Button>
            </li>
            {epochs.map((item) => (
              <li key={item.epoch} className='min-w-0'>
                <Button
                  variant='outline'
                  size='tile'
                  aria-pressed={query.epoch === item.epoch}
                  onClick={() => patch({ epoch: item.epoch })}
                  className={cn(
                    'flex-col items-stretch',
                    query.epoch === item.epoch &&
                      'border-primary/50 bg-primary/10'
                  )}
                >
                  <span className='flex min-w-0 items-center justify-between gap-1'>
                    <Text as='span' weight='semibold'>
                      {`Epoch ${item.epoch}`}
                    </Text>
                    {item.epoch === current && (
                      <Badge size='sm' variant='default'>
                        Now
                      </Badge>
                    )}
                  </span>
                  <Muted as='span' variant='caption'>
                    {item.undone > 0
                      ? `${plural(item.entries, 'page')} · ${item.undone} torn`
                      : plural(item.entries, 'page')}
                  </Muted>
                  <Progress
                    size='sm'
                    value={(item.entries / busiest) * PERCENT}
                    aria-label={`Pages in epoch ${item.epoch}`}
                  />
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className='flex min-w-0 flex-col gap-2 rounded-xl border bg-card p-3'>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <div className='min-w-0 flex-1'>
            <Input
              type='search'
              leadingIcon={Search}
              placeholder='Search the loaded pages'
              aria-label='Search the ledger'
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          {sons.length > 0 && (
            <Select
              value={
                query.actorKind === 'son' && query.actorId !== null
                  ? String(query.actorId)
                  : EVERY_SON
              }
              onValueChange={(value) =>
                patch(
                  value === EVERY_SON
                    ? { actorKind: null, actorId: null }
                    : { actorKind: 'son', actorId: Number(value) }
                )
              }
            >
              <SelectTrigger aria-label='One son' size='sm'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={EVERY_SON}>Any son</SelectItem>
                {sons.map((item) => (
                  <SelectItem key={item.son.id} value={String(item.son.id)}>
                    {item.son.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Button
            size='sm'
            variant={query.actorKind === null ? 'secondary' : 'ghost'}
            aria-pressed={query.actorKind === null}
            onClick={() => chooseActor(null)}
          >
            <Users />
            Everyone
          </Button>
          {actorKinds.map((kind) => {
            const actor = ACTOR[kind]
            const active = query.actorKind === kind && query.actorId === null
            return (
              <Button
                key={kind}
                size='sm'
                variant={active ? 'secondary' : 'ghost'}
                aria-pressed={active}
                onClick={() => chooseActor(kind)}
              >
                <actor.icon />
                {kind === 'creator' && state.data?.creator
                  ? `You (${state.data.creator.name})`
                  : actor.label}
              </Button>
            )
          })}
          {filtered && (
            <Button
              size='sm'
              variant='ghost'
              onClick={() => {
                setSearch('')
                patch({ epoch: null, actorKind: null, actorId: null })
              }}
            >
              <X />
              Clear
            </Button>
          )}
        </div>
      </div>
      {ledger.isPending && <Skeleton className='h-48 w-full' />}
      {ledger.isError && <Text tone='destructive'>{ledger.error.message}</Text>}
      {ledger.data && shown.length === 0 && (
        <EmptyState
          size='compact'
          icon={NotebookPen}
          title={filtered ? 'No page matches' : 'The ledger is empty'}
          description={
            filtered
              ? 'Pick another epoch or actor, or clear the search.'
              : 'Every action of the sons, the mortals, Fate and you is written here as a page.'
          }
        />
      )}
      {groups.map(([epoch, views]) => (
        <section
          key={epoch}
          aria-label={`Epoch ${epoch}`}
          className='flex min-w-0 flex-col gap-2'
        >
          <div className='flex min-w-0 items-center gap-2 border-b pb-1.5'>
            <CalendarDays
              aria-hidden='true'
              className='size-icon-sm text-primary'
            />
            <Text as='span' weight='semibold'>{`Epoch ${epoch}`}</Text>
            <Muted as='span' variant='caption'>
              {plural(views.length, 'page')}
            </Muted>
          </div>
          <ol className='flex min-w-0 flex-col gap-2'>
            {views.map((view) => (
              <LedgerEntry
                key={view.entry.id}
                view={view}
                index={index}
                epochRunning={Boolean(state.data?.epoch_running)}
                result={results.get(view.entry.id)}
                onUndone={(result) =>
                  setResults((current) =>
                    new Map(current).set(view.entry.id, result)
                  )
                }
              />
            ))}
          </ol>
        </section>
      ))}
      {entries.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
          <Muted variant='caption'>
            {`${formatInteger(shown.length)} of ${formatInteger(entries.length)} loaded pages shown`}
          </Muted>
          {full && !capped && pageSize !== null && (
            <Button
              variant='outline'
              size='sm'
              disabled={ledger.isFetching}
              disabledReason='Loading'
              onClick={() =>
                setQuery((value) => ({
                  ...value,
                  limit: Math.min(
                    pageMax ?? Infinity,
                    entries.length + (defaultPageSize ?? pageSize)
                  ),
                }))
              }
            >
              More older pages
            </Button>
          )}
          {capped && (
            <Muted variant='caption'>Pick an epoch to see older pages.</Muted>
          )}
        </div>
      )}
    </div>
  )
}
