import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { navItem } from '@/config/navigation'
import {
  Bell,
  BellDot,
  CalendarDays,
  CheckCheck,
  ChevronDown,
  Clock,
  Eye,
  EyeOff,
  Layers,
  TriangleAlert,
} from 'lucide-react'
import { toast } from 'sonner'
import { queryKeys } from '@/api/queryKeys'
import { fetchJob } from '@/api/system'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import {
  AsideLayout,
  EmptyState,
  Medallion,
  MiniStat,
  Paged,
  PagedList,
  PageHeader,
  Section,
  FieldTile,
} from '@/components/domain'
import { MentionText } from '@/components/domain/MentionText'
import { Label, Muted, Text } from '@/components/typography'
import { useLinkTargets } from '@/features/chronicle/linkTargets'
import { JobItems } from '@/features/epoch/JobItems'
import { NodeLink } from '@/features/feed/NodeLink'
import { type NodeIndex, useNodeIndex } from '@/features/feed/nodes'
import { useRuleValue } from '@/features/world-rules/api'
import { NotificationSettings } from './NotificationSettings'
import { SelfNoteForm } from './SelfNoteForm'
import {
  type NotificationCategory,
  type NotificationRecord,
  useMarkRead,
  useNotificationPages,
  useNotifications,
} from './api'
import {
  CATEGORY_ICON,
  CATEGORY_TONE,
  type NotificationGroup,
  groupNotifications,
  reasonOf,
  subjectOf,
} from './notificationVisuals'

const ITEM = navItem('notifications')
const PAGE_SIZE_RULE = 'server.notification_page_size'
const FALLBACK_PAGE_SIZE = 60
const SUBJECTS_SHOWN = 40
const AUTO_LOAD_MARGIN = '600px'
const SUMMARY_QUERY = {
  category: null,
  unreadOnly: false,
  limit: 1,
  before: null,
}

const dateTime = new Intl.DateTimeFormat('en-US', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

function ReadToggle({ items }: { items: NotificationRecord[] }) {
  const mark = useMarkRead()
  const unread = items.some((item) => !item.is_read)
  const label = unread ? 'Mark read' : 'Mark unread'
  return (
    <Button
      variant='ghost'
      size='icon-sm'
      aria-label={label}
      title={label}
      disabled={mark.isPending}
      disabledReason='Saving'
      onClick={() =>
        mark.mutate(
          { ids: items.map((item) => item.id), every: false, unread: !unread },
          { onError: (error) => toast.error(error.message) }
        )
      }
    >
      {unread ? <Eye /> : <EyeOff />}
    </Button>
  )
}

function WorkDetails({ jobId }: { jobId: string }) {
  const [open, setOpen] = useState(false)
  const job = useQuery({
    queryKey: queryKeys.jobs.detail(jobId),
    queryFn: () => fetchJob(jobId),
    enabled: open,
    staleTime: Infinity,
  })
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Button
        variant='ghost'
        size='sm'
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className='self-start'
      >
        <ChevronDown />
        {open ? 'Hide what was done' : 'What was done'}
      </Button>
      {open && job.isPending && <Skeleton className='h-control-lg w-full' />}
      {open && job.isError && (
        <Text variant='caption' tone='destructive'>
          {job.error.message}
        </Text>
      )}
      {open && job.data && <JobItems items={job.data.items} />}
    </div>
  )
}

function useAutoLoad(enabled: boolean, load: () => void) {
  const sentinel = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const element = sentinel.current
    if (!element || !enabled) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) load()
      },
      { rootMargin: AUTO_LOAD_MARGIN }
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [enabled, load])
  return sentinel
}

function SingleCard({
  item,
  label,
  index,
}: {
  item: NotificationRecord
  label: string
  index: NodeIndex
}) {
  const Icon = CATEGORY_ICON[item.category]
  const targets = useLinkTargets(item.entity_ids ?? [])
  return (
    <li
      data-notification={item.id}
      data-read={item.is_read || undefined}
      className={cn(
        'flex min-w-0 gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3',
        item.is_read ? 'bg-card' : 'border-primary/40 bg-primary/5'
      )}
    >
      <Medallion
        icon={Icon}
        tone={item.is_read ? 'muted' : CATEGORY_TONE[item.category]}
        size='sm'
      />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <div className='flex min-w-0 items-start gap-2'>
          <Text
            weight={item.is_read ? 'normal' : 'semibold'}
            className='min-w-0 flex-1'
          >
            <MentionText text={item.title} targets={targets} />
          </Text>
          <ReadToggle items={[item]} />
        </div>
        {item.body && item.body !== item.title && (
          <Muted variant='caption' truncate={4}>
            <MentionText text={item.body} targets={targets} />
          </Muted>
        )}
        {item.job_id && <WorkDetails jobId={item.job_id} />}
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge
            size='sm'
            variant={item.category === 'achievement' ? 'default' : 'outline'}
          >
            <Icon />
            {label}
          </Badge>
          <Badge size='sm' variant='outline'>
            <Clock />
            {dateTime.format(new Date(item.created_at))}
          </Badge>
          {!item.is_read && (
            <Badge size='sm' variant='default'>
              New
            </Badge>
          )}
          {item.target_node_id !== null && (
            <Text as='span' variant='caption'>
              <NodeLink
                nodeId={item.target_node_id}
                index={index}
                fallback={null}
              />
            </Text>
          )}
        </div>
      </div>
    </li>
  )
}

function SubjectName({ item }: { item: NotificationRecord }) {
  const targets = useLinkTargets(item.entity_ids ?? [])
  return <MentionText text={subjectOf(item)} targets={targets} />
}

function GroupCard({ group }: { group: NotificationGroup }) {
  const first = group.items[0]
  const last = group.items[group.items.length - 1]
  const unread = group.items.filter((item) => !item.is_read).length
  const reason = reasonOf(first) ?? first.title
  return (
    <li
      className={cn(
        'flex min-w-0 gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3',
        unread > 0 ? 'border-warning/40 bg-warning/5' : 'bg-card'
      )}
    >
      <Medallion
        icon={TriangleAlert}
        tone={unread > 0 ? 'warning' : 'muted'}
        size='sm'
      />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <div className='flex min-w-0 items-start gap-2'>
          <Text weight='semibold' className='min-w-0 flex-1'>
            {`${formatInteger(group.items.length)} background tasks failed for the same reason`}
          </Text>
          <ReadToggle items={group.items} />
        </div>
        <Muted variant='caption' truncate={3}>
          {reason}
        </Muted>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant='warning'>
            <Layers />
            {`×${formatInteger(group.items.length)}`}
          </Badge>
          {unread > 0 && (
            <Badge size='sm' variant='default'>
              {`${formatInteger(unread)} new`}
            </Badge>
          )}
          <Badge size='sm' variant='outline'>
            <Clock />
            {`${dateTime.format(new Date(last.created_at))} – ${dateTime.format(new Date(first.created_at))}`}
          </Badge>
        </div>
        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button variant='ghost' size='sm' className='w-fit'>
              <ChevronDown />
              Which tasks
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <PagedList
              items={group.items}
              initial={SUBJECTS_SHOWN}
              noun={['task', 'tasks']}
              className='flex min-w-0 flex-wrap gap-1.5 pt-1'
              itemKey={(item) => item.id}
            >
              {(item) => (
                <li>
                  <Badge size='sm' variant='outline'>
                    <SubjectName item={item} />
                  </Badge>
                </li>
              )}
            </PagedList>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </li>
  )
}

export function NotificationsScreen() {
  const [category, setCategory] = useState<NotificationCategory | null>(null)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [showErrors, setShowErrors] = useState(false)
  const summary = useNotifications(SUMMARY_QUERY)
  const pageSize = useRuleValue(PAGE_SIZE_RULE) ?? FALLBACK_PAGE_SIZE
  const exclude: NotificationCategory[] =
    category === null && !showErrors ? ['error'] : []
  const pages = useNotificationPages(category, unreadOnly, pageSize, exclude)
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = pages
  const loadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage)
      void fetchNextPage({ cancelRefetch: false })
  }, [fetchNextPage, hasNextPage, isFetchingNextPage])
  const sentinel = useAutoLoad(Boolean(hasNextPage), loadMore)
  const mark = useMarkRead()
  const index = useNodeIndex()
  const list = summary.data
  const labels = new Map(
    (list?.categories ?? []).map((info) => [info.category, info.label])
  )
  const items = useMemo(
    () => (pages.data?.pages ?? []).flatMap((page) => page.items),
    [pages.data]
  )
  const epochs = useMemo(() => {
    const map = new Map<string, NotificationRecord[]>()
    for (const item of items) {
      const key = item.epoch === null ? 'none' : String(item.epoch)
      map.set(key, [...(map.get(key) ?? []), item])
    }
    return [...map.entries()].map(
      ([key, members]) => [key, groupNotifications(members)] as const
    )
  }, [items])
  const counts = list?.counts ?? []
  const total = counts.reduce((sum, count) => sum + count.total, 0)
  const errors = counts.find((count) => count.category === 'error')
  const unreadHere = category
    ? (counts.find((count) => count.category === category)?.unread ?? 0)
    : (list?.unread ?? 0)
  const markAll = () =>
    mark.mutate(
      { every: true, category, unread: false },
      {
        onSuccess: (result) =>
          toast.success(`${formatInteger(result.changed)} marked read`),
        onError: (error) => toast.error(error.message),
      }
    )

  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
        meta={
          list && (
            <Badge variant={list.unread > 0 ? 'default' : 'outline'}>
              {list.unread > 0
                ? `${formatInteger(list.unread)} unread`
                : 'All read'}
            </Badge>
          )
        }
      />
      {summary.isError && (
        <Text tone='destructive'>{summary.error.message}</Text>
      )}
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <MiniStat
          icon={BellDot}
          label='Unread'
          value={list?.unread ?? 0}
          tone={(list?.unread ?? 0) > 0 ? 'gold' : 'success'}
        />
        <MiniStat icon={Bell} label='All notices' value={total} tone='info' />
        <MiniStat
          icon={Layers}
          label='Kinds of news'
          value={counts.filter((count) => count.total > 0).length}
          tone='verdigris'
        />
        <MiniStat
          icon={TriangleAlert}
          label='Unread errors'
          value={errors?.unread ?? 0}
          tone={(errors?.unread ?? 0) > 0 ? 'warning' : 'muted'}
          hint='Background tasks that failed; repeated failures are folded into one card'
        />
      </div>
      {errors && errors.total > 0 && category !== 'error' && (
        <div
          data-notification-errors
          className={cn(
            'flex min-w-0 flex-wrap items-center gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3',
            errors.unread > 0 ? 'border-warning/40 bg-warning/5' : 'bg-muted/30'
          )}
        >
          <Medallion
            icon={TriangleAlert}
            tone={errors.unread > 0 ? 'warning' : 'muted'}
            size='sm'
          />
          <div className='flex min-w-0 flex-1 basis-60 flex-col'>
            <Text as='span' weight='semibold'>
              {`${formatInteger(errors.total)} system errors`}
            </Text>
            <Muted as='span' variant='caption'>
              {showErrors
                ? 'They are mixed into the list below.'
                : 'Kept out of the news below so the world stays readable.'}
              {errors.unread > 0 &&
                ` ${formatInteger(errors.unread)} of them are new.`}
            </Muted>
          </div>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Button
              variant='outline'
              size='sm'
              onClick={() => setCategory('error')}
            >
              <Layers />
              Review them
            </Button>
            {category === null && (
              <Button
                variant='ghost'
                size='sm'
                aria-pressed={showErrors}
                onClick={() => setShowErrors(!showErrors)}
              >
                {showErrors ? <EyeOff /> : <Eye />}
                {showErrors ? 'Hide from the list' : 'Show in the list'}
              </Button>
            )}
            <Button
              variant='ghost'
              size='sm'
              disabled={errors.unread === 0 || mark.isPending}
              disabledReason='No unread errors'
              onClick={() =>
                mark.mutate(
                  { every: true, category: 'error', unread: false },
                  {
                    onSuccess: (result) =>
                      toast.success(
                        `${plural(result.changed, 'error', 'errors')} marked read`
                      ),
                    onError: (error) => toast.error(error.message),
                  }
                )
              }
            >
              <CheckCheck />
              Mark them read
            </Button>
          </div>
        </div>
      )}
      {list && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Kinds of news</Label>
          <ul className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5 2xl:grid-cols-8'>
            <li className='min-w-0'>
              <Button
                variant='outline'
                size='tile'
                aria-pressed={category === null}
                onClick={() => setCategory(null)}
                className={cn(
                  category === null && 'border-primary/50 bg-primary/10'
                )}
              >
                <Medallion icon={Bell} tone='gold' size='sm' />
                <span className='flex min-w-0 flex-1 flex-col'>
                  <Text as='span' weight='semibold' truncate>
                    Everything
                  </Text>
                  <Muted as='span' variant='caption'>
                    {`${formatInteger(list.unread)} new · ${formatInteger(total)}`}
                  </Muted>
                </span>
              </Button>
            </li>
            <Paged items={counts.filter((count) => count.total > 0)} as='li'>
              {(count) => {
                const Icon = CATEGORY_ICON[count.category]
                const active = category === count.category
                return (
                  <li key={count.category} className='min-w-0'>
                    <Button
                      variant='outline'
                      size='tile'
                      aria-pressed={active}
                      onClick={() => setCategory(count.category)}
                      className={cn(
                        active && 'border-primary/50 bg-primary/10'
                      )}
                    >
                      <Medallion
                        icon={Icon}
                        tone={
                          count.unread > 0
                            ? CATEGORY_TONE[count.category]
                            : 'muted'
                        }
                        size='sm'
                      />
                      <span className='flex min-w-0 flex-1 flex-col'>
                        <Text as='span' weight='semibold' truncate>
                          {labels.get(count.category) ?? count.category}
                        </Text>
                        <Muted as='span' variant='caption' truncate>
                          {count.unread > 0
                            ? `${formatInteger(count.unread)} new · ${formatInteger(count.total)}`
                            : formatInteger(count.total)}
                        </Muted>
                      </span>
                    </Button>
                  </li>
                )
              }}
            </Paged>
          </ul>
        </div>
      )}
      <AsideLayout
        aside={
          <>
            <SelfNoteForm />
            {list && (
              <NotificationSettings
                key={JSON.stringify(list.settings)}
                list={list}
              />
            )}
          </>
        }
      >
        <Section
          title={
            category
              ? (labels.get(category) ?? category)
              : 'News from the world'
          }
          description='Deaths, rebellions, prophecies, cosmic events and the prayers made to you collect here.'
          surface='card'
          actions={
            <div className='flex min-w-0 flex-wrap items-center gap-3'>
              <div className='flex items-center gap-2'>
                <FieldTile id='only-unread' label='Only unread'>
                  <Switch
                    id='only-unread'
                    checked={unreadOnly}
                    onCheckedChange={setUnreadOnly}
                  />
                </FieldTile>
              </div>
              <Button
                variant='outline'
                size='sm'
                disabled={unreadHere === 0 || mark.isPending}
                disabledReason={
                  unreadHere === 0 ? 'Nothing is unread' : 'Saving'
                }
                onClick={markAll}
              >
                <CheckCheck />
                {category ? 'Mark these read' : 'Mark all read'}
              </Button>
            </div>
          }
        >
          {(pages.isPending || summary.isPending) && (
            <Skeleton className='h-48 w-full' />
          )}
          {pages.isError && (
            <Text tone='destructive'>{pages.error.message}</Text>
          )}
          {pages.data && items.length === 0 && (
            <EmptyState
              size='compact'
              icon={Bell}
              title={unreadOnly ? 'Nothing unread here' : 'No news here yet'}
              description='Pick another kind of news, or turn off Only unread.'
            />
          )}
          {epochs.map(([key, groups]) => (
            <section
              key={key}
              aria-label={
                key === 'none' ? 'Outside the epochs' : `Epoch ${key}`
              }
              className='flex min-w-0 flex-col gap-2'
            >
              <div className='flex min-w-0 items-center gap-2 border-b pb-1.5'>
                <CalendarDays
                  aria-hidden='true'
                  className='size-icon-sm text-primary'
                />
                <Text as='span' weight='semibold'>
                  {key === 'none' ? 'Outside the epochs' : `Epoch ${key}`}
                </Text>
                <Muted as='span' variant='caption'>
                  {`${plural(
                    groups.reduce((sum, group) => sum + group.items.length, 0),
                    'notice',
                    'notices'
                  )}`}
                </Muted>
              </div>
              <ol className='flex min-w-0 flex-col gap-2'>
                <Paged items={groups} as='li'>
                  {(group) =>
                    group.items.length > 1 ? (
                      <GroupCard key={group.key} group={group} />
                    ) : (
                      <SingleCard
                        key={group.key}
                        item={group.items[0]}
                        label={
                          labels.get(group.items[0].category) ??
                          group.items[0].category
                        }
                        index={index}
                      />
                    )
                  }
                </Paged>
              </ol>
            </section>
          ))}
          <div ref={sentinel} aria-hidden='true' />
          {pages.isFetchingNextPage && <Skeleton className='h-24 w-full' />}
          {hasNextPage && !isFetchingNextPage && (
            <Button
              variant='outline'
              className='self-center'
              onClick={loadMore}
            >
              <ChevronDown />
              Show older notifications
            </Button>
          )}
          {pages.data && !pages.hasNextPage && items.length > 0 && (
            <Muted variant='caption'>That is everything.</Muted>
          )}
        </Section>
      </AsideLayout>
    </>
  )
}
