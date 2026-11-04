import { useMemo, useState } from 'react'
import {
  Book,
  BookOpen,
  CircleCheck,
  EyeOff,
  GitBranch,
  GraduationCap,
  Lock,
  Plus,
  Sparkles,
  Target,
  TriangleAlert,
  Users,
  X,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { knowledgeBranchValues } from '@/api/generated/schema'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  IconStat,
  KpiTile,
  type KpiTone,
  Medallion,
  Section,
  Paged,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { tierNumeral } from '@/features/languages/languageIcons'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { LearningShaping } from './LearningControls'
import {
  AdjustBlock,
  AdjustPanel,
  ChoicePicker,
  LoreCard,
  RefChip,
  RowEditor,
  RowEditors,
} from './LoreFields'
import { type LearningCard, useLearning } from './api'
import { KPI_GRID, MAX_LEVEL, PERCENT, branchOf, busyOf } from './model'

type Level = LearningCard['levels'][number]
type Technique = LearningCard['techniques'][number]

const PIP_TONE: Record<KpiTone, string> = {
  gold: 'bg-primary',
  verdigris: 'bg-brand-verdigris',
  info: 'bg-info',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-destructive',
  muted: 'bg-muted-foreground',
}

function Pips({ level, tone }: { level: number; tone: KpiTone }) {
  return (
    <span
      role='img'
      aria-label={`Level ${level} of ${MAX_LEVEL}`}
      className='flex min-w-0 items-center gap-0.5'
    >
      {Array.from({ length: MAX_LEVEL }, (_, index) => (
        <span
          key={index}
          className={cn(
            'h-meter-md min-w-0 flex-1 rounded-full',
            index < level ? PIP_TONE[tone] : 'bg-muted'
          )}
        />
      ))}
    </span>
  )
}

function BranchRow({ row }: { row: Level }) {
  const spec = branchOf(row.branch)
  return (
    <li
      data-surface='HolderLevel'
      className={cn(
        'flex min-w-0 items-center gap-3 rounded-lg border bg-muted/30 p-2.5 @xl/lore:last:odd:col-span-2',
        !row.open && 'border-warning/40'
      )}
    >
      <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <div className='flex min-w-0 items-center gap-2'>
          <Text as='span' weight='semibold' className='min-w-0 flex-1' truncate>
            {spec.label}
          </Text>
          <Stat value={row.level} unit={`/ ${MAX_LEVEL}`} />
        </div>
        <Pips level={row.level} tone={spec.tone} />
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <IconStat
            icon={Users}
            label='Practitioners'
            value={row.practitioners}
            tone='info'
            hint='People who practise it; if they all die with no book or master, a level can be lost'
          />
          {!row.open && (
            <Badge size='sm' variant='warning'>
              <Lock aria-hidden='true' />
              Gate shut
            </Badge>
          )}
          {row.secret && (
            <Badge size='sm' variant='secondary'>
              <EyeOff aria-hidden='true' />
              Secret
            </Badge>
          )}
          {row.locked.length > 0 && (
            <Badge size='sm' variant='default'>
              <Lock aria-hidden='true' />
              Held
            </Badge>
          )}
        </div>
      </div>
    </li>
  )
}

function TechniqueTile({
  holderId,
  row,
  reached,
  blocked,
}: {
  holderId: number
  row: Technique
  reached: number
  blocked: string | null
}) {
  const set = useGodAction<{ held: boolean; secret: boolean }>({
    run: ({ held, secret }) =>
      unwrap(
        api.POST('/api/actions/research:technique', {
          body: { holder_id: holderId, technique: row.technique, held, secret },
        })
      ),
  })
  const busy = busyOf(blocked, set.isPending)
  const branch = branchOf(row.branch)
  const open = row.reachable && !row.known
  return (
    <li
      data-surface='TechniqueNode'
      data-state={row.known ? 'known' : open ? 'reachable' : 'locked'}
      className={cn(
        'flex h-full min-w-0 flex-col gap-2 rounded-lg border p-3 @md/lore:last:odd:col-span-2',
        row.known &&
          'border-primary/50 bg-primary/8 shadow-md ring-1 shadow-primary/10 ring-primary/20',
        open && 'border-info/40 bg-info/5',
        !row.known && !open && 'border-dashed bg-muted/20'
      )}
    >
      <div className='flex min-w-0 items-start gap-2.5'>
        <Medallion
          icon={row.known ? CircleCheck : open ? branch.icon : Lock}
          tone={row.known ? 'gold' : open ? 'info' : 'muted'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text
            as='span'
            weight='semibold'
            tone={row.known || open ? 'default' : 'muted'}
          >
            {row.label}
          </Text>
          <Muted variant='caption'>{row.effect}</Muted>
        </div>
        <Badge size='sm' variant={row.known ? 'default' : 'outline'}>
          {`Tier ${tierNumeral(row.level)}`}
        </Badge>
      </div>
      <div className='mt-auto flex min-w-0 flex-wrap items-center gap-2'>
        {row.known ? (
          <>
            <Badge variant='default'>
              <Sparkles aria-hidden='true' />
              Known
            </Badge>
            <label className='flex items-center gap-1.5'>
              <Switch
                checked={row.secret}
                disabled={busy !== null}
                aria-label='Keep it secret'
                onCheckedChange={(secret) => set.mutate({ held: true, secret })}
              />
              <Muted as='span' variant='caption'>
                Secret
              </Muted>
            </label>
            <Button
              size='sm'
              variant='ghost'
              className='ml-auto'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => set.mutate({ held: false, secret: false })}
            >
              <X />
              Forget it
            </Button>
          </>
        ) : (
          <>
            {open ? (
              <Badge variant='info'>
                <Target aria-hidden='true' />
                Within reach
              </Badge>
            ) : (
              <Badge variant='secondary'>
                <Lock aria-hidden='true' />
                {reached >= row.level
                  ? 'Its gate is not yet met'
                  : `Needs ${branch.label.toLowerCase()} ${row.level}`}
              </Badge>
            )}
            <Button
              size='sm'
              variant={open ? 'default' : 'outline'}
              className='ml-auto'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => set.mutate({ held: true, secret: false })}
            >
              <Plus />
              Teach it
            </Button>
          </>
        )}
      </div>
    </li>
  )
}

function TechniqueGroup({
  branch,
  rows,
  level,
  holderId,
  blocked,
}: {
  branch: string
  rows: Technique[]
  level: number
  holderId: number
  blocked: string | null
}) {
  const spec = branchOf(branch)
  const known = rows.filter((row) => row.known).length
  return (
    <div
      data-surface='TechniqueBranch'
      className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <div className='flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1'>
            <Text as='span' weight='semibold'>
              {spec.label}
            </Text>
            <Badge size='sm' variant={level > 0 ? 'default' : 'secondary'}>
              {level > 0 ? `Level ${level}` : 'Not begun'}
            </Badge>
            <Muted as='span' variant='caption' className='ml-auto'>
              {`${known} of ${rows.length} known`}
            </Muted>
          </div>
          <Progress
            value={(known / Math.max(1, rows.length)) * PERCENT}
            size='sm'
            aria-label={`${spec.label} techniques known`}
          />
        </div>
      </div>
      <ul className='grid min-w-0 grid-cols-1 gap-2 @md/lore:grid-cols-2'>
        <Paged items={rows} as='li'>
          {(row) => (
            <TechniqueTile
              key={row.technique}
              holderId={holderId}
              row={row}
              reached={level}
              blocked={blocked}
            />
          )}
        </Paged>
      </ul>
    </div>
  )
}

function LearningControls({
  card,
  blocked,
}: {
  card: LearningCard
  blocked: string | null
}) {
  const [branch, setBranch] = useState('')
  const set = useGodAction<{ branch: string; level: number }>({
    run: ({ branch: chosen, level }) =>
      unwrap(
        api.POST('/api/actions/research:level', {
          body: {
            holder_id: card.holder_id,
            branch: chosen as 'agriculture',
            level,
          },
        })
      ),
  })
  const busy = busyOf(blocked, set.isPending)
  const known = card.levels.map((row) => row.branch as string)
  const choices = Object.fromEntries(
    knowledgeBranchValues
      .filter((item) => !known.includes(item))
      .map((item) => [item, branchOf(item)])
  )
  return (
    <AdjustPanel
      surface='LearningAdjust'
      title='Shape their learning'
      note='Open a new branch or set any level. Techniques are taught and forgotten on their own cards above. Every change goes into the ledger and can be undone.'
    >
      <AdjustBlock title='Open a branch' icon={GitBranch}>
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <div className='min-w-0 flex-1 basis-48'>
            <ChoicePicker
              label='Branch of learning'
              value={branch}
              table={choices}
              blocked={busy}
              placeholder='Choose'
              onPick={setBranch}
            />
          </div>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || branch === ''}
            disabledReason={
              busy ?? (branch === '' ? 'Choose a branch' : undefined)
            }
            onClick={() => {
              set.mutate({ branch, level: 1 })
              setBranch('')
            }}
          >
            <Plus />
            Begin it
          </Button>
        </div>
      </AdjustBlock>
      {card.levels.length > 0 && (
        <AdjustBlock title='Levels' icon={GraduationCap}>
          <RowEditors>
            <Paged items={card.levels}>
              {(row) => {
                const spec = branchOf(row.branch)
                return (
                  <RowEditor
                    key={`${row.branch}-${row.level}`}
                    label={`${spec.label} level`}
                    icon={spec.icon}
                    value={row.level}
                    max={MAX_LEVEL}
                    blocked={busy}
                    onSave={(level) =>
                      set.mutate({ branch: row.branch, level })
                    }
                  />
                )
              }}
            </Paged>
          </RowEditors>
        </AdjustBlock>
      )}
      <LearningShaping
        holderId={card.holder_id}
        card={card}
        blocked={blocked}
      />
    </AdjustPanel>
  )
}

function Body({
  card,
  blocked,
}: {
  card: LearningCard
  blocked: string | null
}) {
  const levels = useMemo(
    () => new Map(card.levels.map((row) => [row.branch as string, row.level])),
    [card.levels]
  )
  const groups = useMemo(() => {
    const found = new Map<string, Technique[]>()
    for (const row of card.techniques)
      found.set(row.branch, [...(found.get(row.branch) ?? []), row])
    return [...found.entries()]
      .map(
        ([branch, rows]) =>
          [
            branch,
            [...rows].sort(
              (left, right) =>
                left.level - right.level ||
                left.label.localeCompare(right.label)
            ),
          ] as const
      )
      .sort(
        ([left], [right]) =>
          (levels.get(right) ?? 0) - (levels.get(left) ?? 0) ||
          left.localeCompare(right)
      )
  }, [card.techniques, levels])
  const ordered = [...card.levels].sort(
    (left, right) =>
      right.level - left.level || left.branch.localeCompare(right.branch)
  )
  const deepest = ordered[0]
  const knownCount = card.techniques.filter((row) => row.known).length
  const reach = card.techniques.filter(
    (row) => row.reachable && !row.known
  ).length
  return (
    <div className='@container/lore flex min-w-0 flex-col gap-4'>
      <div className={KPI_GRID}>
        <KpiTile
          label='Branches'
          value={card.levels.length}
          icon={GitBranch}
          tone='verdigris'
          hint={`${knowledgeBranchValues.length - card.levels.length} more remain unopened`}
          meter={{
            value: card.levels.length,
            max: knowledgeBranchValues.length,
            label: 'Branches opened',
          }}
        />
        <KpiTile
          label='Deepest learning'
          value={deepest ? `Level ${deepest.level}` : 'None'}
          icon={deepest ? branchOf(deepest.branch).icon : GraduationCap}
          hint={
            deepest
              ? `${branchOf(deepest.branch).label}, of ${MAX_LEVEL} levels`
              : 'They have learned nothing yet'
          }
          meter={{
            value: deepest?.level ?? 0,
            max: MAX_LEVEL,
            label: 'Deepest level',
          }}
        />
        <KpiTile
          label='Techniques'
          value={`${knownCount}/${card.techniques.length}`}
          icon={CircleCheck}
          tone='success'
          hint='Known techniques change how they farm, build, fight and heal'
          meter={{
            value: knownCount,
            max: Math.max(1, card.techniques.length),
            label: 'Techniques known',
          }}
        />
        <KpiTile
          label='Within reach'
          value={reach}
          icon={Target}
          tone={reach > 0 ? 'info' : 'muted'}
          hint='Their gates are met; the world may adopt them any epoch'
        />
      </div>
      <LoreCard
        title='Branches of learning'
        icon={GraduationCap}
        tone='verdigris'
        aside={<Badge variant='secondary'>{card.levels.length}</Badge>}
      >
        {ordered.length === 0 ? (
          <Muted>They have learned nothing yet.</Muted>
        ) : (
          <ul className='grid min-w-0 grid-cols-1 gap-2 @xl/lore:grid-cols-2'>
            <Paged items={ordered} as='li'>
              {(row) => <BranchRow key={row.branch} row={row} />}
            </Paged>
          </ul>
        )}
      </LoreCard>
      <LoreCard
        title='Books that keep it'
        icon={BookOpen}
        tone='info'
        aside={<Badge variant='secondary'>{card.books.length}</Badge>}
      >
        {card.books.length === 0 ? (
          <Muted>
            No book keeps their learning; what dies with its practitioners is
            lost.
          </Muted>
        ) : (
          <ul
            data-surface='HolderBooks'
            className='flex min-w-0 flex-wrap gap-1.5'
          >
            <Paged items={card.books} as='li'>
              {(book) => (
                <li key={book.id}>
                  <RefChip icon={Book} label='' item={book} />
                </li>
              )}
            </Paged>
          </ul>
        )}
      </LoreCard>
      <div data-surface='TechGraph' className='flex min-w-0 flex-col gap-3'>
        <div className='flex min-w-0 items-center gap-2'>
          <Label variant='overline' className='flex-1'>
            Technique tree
          </Label>
          <Badge variant='default'>
            <CircleCheck aria-hidden='true' />
            {`${knownCount} known`}
          </Badge>
          <Badge variant='info'>
            <Target aria-hidden='true' />
            {`${reach} within reach`}
          </Badge>
        </div>
        <Paged items={groups}>
          {([branch, rows]) => (
            <TechniqueGroup
              key={branch}
              branch={branch}
              rows={rows}
              level={levels.get(branch) ?? 0}
              holderId={card.holder_id}
              blocked={blocked}
            />
          )}
        </Paged>
      </div>
      <LearningControls card={card} blocked={blocked} />
    </div>
  )
}

export function LearningSection({
  holderId,
  readOnlyReason,
}: {
  holderId: number
  readOnlyReason?: string | null
}) {
  const view = useLearning(holderId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  return (
    <Section
      id='section-learning'
      title='Learning'
      description='Levels of knowledge, the techniques they open, and the books that keep them.'
      icon={GraduationCap}
    >
      {view.isPending && <Muted>Reading what they know…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Their learning could not be read'
          description={view.error.message}
        />
      )}
      {view.data && <Body card={view.data} blocked={blocked} />}
    </Section>
  )
}
