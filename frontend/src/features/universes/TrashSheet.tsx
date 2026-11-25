import { useState } from 'react'
import {
  CalendarClock,
  Eraser,
  HardDrive,
  Hourglass,
  LoaderCircle,
  Trash2,
  Undo2,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatDateTime, formatSince } from '@/lib/format'
import { formatBytes, plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  ConfirmDialog,
  EmptyState,
  LoadingBlock,
  Medallion,
  MiniStat,
  StatBar,
} from '@/components/domain'
import { Text } from '@/components/typography'
import { ServerShowMore } from './ServerShowMore'
import { UniverseCrest } from './UniverseCrest'
import { useEmptyTrash, usePurgeTrash, useRestoreTrash, useTrash } from './api'
import { type TrashedUniverse } from './types'

const DAY_MS = 86_400_000
const SOON_DAYS = 3

function daysLeft(item: TrashedUniverse, now: number): number {
  return Math.max(0, Math.ceil((Date.parse(item.purge_at) - now) / DAY_MS))
}

function TrashRow({
  item,
  keepDays,
  now,
  onPurge,
}: {
  item: TrashedUniverse
  keepDays: number
  now: number
  onPurge: () => void
}) {
  const restore = useRestoreTrash()
  const left = daysLeft(item, now)
  return (
    <li className='flex min-w-0 flex-col gap-3 rounded-lg surface-framed p-3'>
      <div className='flex min-w-0 items-center gap-3'>
        <UniverseCrest name={item.name} size='md' />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text weight='semibold' truncate className='font-display'>
            {item.name}
          </Text>
          <div className='flex min-w-0 flex-wrap gap-1'>
            <Badge
              variant='secondary'
              size='sm'
              title={formatDateTime(item.deleted_at)}
            >
              <Trash2 />
              {`Deleted ${formatSince(item.deleted_at, now)}`}
            </Badge>
            <Badge variant='secondary' size='sm'>
              <HardDrive />
              {formatBytes(item.size_bytes)}
            </Badge>
          </div>
        </div>
      </div>
      <div title={`Purged for good on ${formatDateTime(item.purge_at)}`}>
        <StatBar
          framed
          icon={Hourglass}
          label={
            left === 0
              ? 'Purged at the next sweep'
              : `${plural(left, 'day')} until it is purged`
          }
          value={left}
          max={Math.max(keepDays, 1)}
          tone={left <= SOON_DAYS ? 'destructive' : 'warning'}
        />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <Button
          act={restore}
          type='button'
          size='sm'
          disabled={restore.isPending}
          disabledReason='It is being brought back.'
          onClick={() =>
            restore.mutate(item.id, {
              onSuccess: () =>
                toast.success(`${item.name} is back on the shelf`),
              onError: (error) => toast.error(error.message),
            })
          }
        >
          {restore.isPending ? (
            <LoaderCircle className='animate-spin motion-reduce:animate-none' />
          ) : (
            <Undo2 />
          )}
          Bring it back
        </Button>
        <Button
          type='button'
          size='sm'
          variant='destructive'
          disabled={restore.isPending}
          disabledReason='It is being brought back.'
          onClick={onPurge}
        >
          <Eraser />
          Purge now
        </Button>
      </div>
    </li>
  )
}

type Purging = { kind: 'one'; item: TrashedUniverse } | { kind: 'all' }

export function TrashSheet({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const trash = useTrash()
  const purge = usePurgeTrash()
  const empty = useEmptyTrash()
  const [purging, setPurging] = useState<Purging | null>(null)
  const [now] = useState(() => Date.now())
  const pages = trash.data?.pages ?? []
  const first = pages[0]
  const shown = pages.flatMap((page) => page.items)
  const total = first?.total ?? 0
  const keepDays = first?.keep_days ?? 0
  const soonest = shown.reduce<TrashedUniverse | null>(
    (best, item) =>
      best === null || Date.parse(item.purge_at) < Date.parse(best.purge_at)
        ? item
        : best,
    null
  )
  const busy = purge.isPending || empty.isPending
  const confirmPurge = () => {
    if (purging === null) return
    if (purging.kind === 'all') {
      empty.mutate(undefined, {
        onSuccess: (result) => {
          toast.success(
            `The trash is empty: ${plural(result.purged, 'universe')} gone for good`
          )
          setPurging(null)
        },
        onError: (error) => toast.error(error.message),
      })
      return
    }
    const { item } = purging
    purge.mutate(item.id, {
      onSuccess: () => {
        toast.success(`${item.name} is gone for good`)
        setPurging(null)
      },
      onError: (error) => toast.error(error.message),
    })
  }
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className='w-full gap-0 sm:max-w-md'>
        <SheetHeader>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={Trash2} tone='danger' />
            <SheetTitle>The trash</SheetTitle>
          </div>
          <SheetDescription>
            {`Deleted universes wait here ${keepDays > 0 ? `for ${plural(keepDays, 'day')}` : 'until their purge date'}. Bring one back to the shelf, or purge it for good.`}
          </SheetDescription>
        </SheetHeader>
        <div className='flex min-h-0 min-w-0 flex-1 flex-col gap-3 overflow-y-auto px-4 pb-4'>
          {trash.isPending ? (
            <LoadingBlock label='Reading the trash' />
          ) : trash.isError ? (
            <EmptyState
              size='compact'
              icon={Trash2}
              title='The trash could not be read'
              description={trash.error.message}
              action={
                <Button
                  type='button'
                  variant='outline'
                  onClick={() => void trash.refetch()}
                >
                  Try again
                </Button>
              }
            />
          ) : shown.length === 0 ? (
            <EmptyState
              size='compact'
              icon={Trash2}
              title='The trash is empty'
              description='Universes you delete come here first, so a slip of the hand is never final.'
            />
          ) : (
            <>
              {total > 0 && (
                <div className='grid min-w-0 grid-cols-2 gap-2'>
                  <MiniStat
                    icon={HardDrive}
                    label={plural(total, 'universe')}
                    value={formatBytes(first?.held_bytes ?? 0)}
                    tone='warning'
                  />
                  <MiniStat
                    icon={CalendarClock}
                    label='Next purge'
                    value={
                      soonest
                        ? formatSince(soonest.purge_at, now)
                        : 'Nothing waits'
                    }
                    tone='danger'
                  />
                </div>
              )}
              <ul
                aria-label='Trashed universes'
                className='flex min-w-0 flex-col gap-3'
              >
                {shown.map((item) => (
                  <TrashRow
                    key={item.id}
                    item={item}
                    keepDays={keepDays}
                    now={now}
                    onPurge={() => setPurging({ kind: 'one', item })}
                  />
                ))}
              </ul>
              <ServerShowMore
                shown={shown.length}
                total={total}
                more={trash.hasNextPage}
                loading={trash.isFetchingNextPage}
                onMore={() => void trash.fetchNextPage()}
              />
            </>
          )}
        </div>
        <SheetFooter>
          <Button
            act={empty}
            type='button'
            variant='destructive'
            disabled={total === 0 || busy}
            disabledReason={
              total === 0 ? 'The trash is already empty.' : 'Purging.'
            }
            onClick={() => setPurging({ kind: 'all' })}
          >
            <Eraser />
            Empty the trash
          </Button>
        </SheetFooter>
      </SheetContent>
      <ConfirmDialog
        act={[empty, purge]}
        open={purging !== null}
        onOpenChange={(next) => {
          if (!next && !busy) setPurging(null)
        }}
        destructive
        title={
          purging?.kind === 'one'
            ? `Purge ${purging.item.name}?`
            : 'Empty the trash?'
        }
        desc={
          purging?.kind === 'one'
            ? `${purging.item.name} and every record and image it holds are removed for good. This cannot be undone.`
            : `${plural(total, 'universe')} and every record and image they hold, ${formatBytes(first?.held_bytes ?? 0)} in all, are removed for good. This cannot be undone.`
        }
        confirmText={
          <>
            <Eraser />
            {purging?.kind === 'one'
              ? `Purge ${purging.item.name}`
              : 'Empty the trash'}
          </>
        }
        isLoading={busy}
        handleConfirm={confirmPurge}
      />
    </Sheet>
  )
}
