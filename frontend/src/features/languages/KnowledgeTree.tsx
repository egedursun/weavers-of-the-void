import { useMemo, useState } from 'react'
import {
  ExternalLink,
  FlaskConical,
  Lightbulb,
  Lock,
  Search,
  Sparkles,
  Unlock,
  Users,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { EmptyState, EntityLink, Medallion, Section } from '@/components/domain'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { Label, Muted, SectionTitle, Text } from '@/components/typography'
import { humanize } from '@/features/entity/actions/schema'
import { type KnowledgeView } from '@/features/entity/api/types'
import { TechBoard } from './TechBoard'
import {
  BRANCH_ICON,
  COSMIC_BRANCHES,
  type KnowledgeBranch,
  tierNumeral,
} from './languageIcons'
import { tierOf } from './treeLayout'

const UNSORTED = 'unsorted'
const PERCENT = 100
const KNOWER_LIMIT = 16
const SEARCH_LIMIT = 8

type BranchKey = KnowledgeBranch | typeof UNSORTED

type NodeRef = KnowledgeView['knowers'][number]

const REF_KIND: Partial<Record<NodeRef['kind'], DrawerKind>> = {
  entity: 'entity',
  son: 'son',
  foreign_god: 'foreign-god',
}

function RefLink({ node }: { node: NodeRef }) {
  const kind = REF_KIND[node.kind]
  if (!kind) return <Text as='span'>{node.name}</Text>
  return (
    <EntityLink kind={kind} id={String(node.id)}>
      {node.name}
    </EntityLink>
  )
}

type BranchSummary = {
  key: BranchKey
  items: KnowledgeView[]
  top: number
  keepers: number
}

function BranchTile({
  summary,
  peak,
  active,
  onSelect,
}: {
  summary: BranchSummary
  peak: number
  active: boolean
  onSelect: () => void
}) {
  const Icon = summary.key === UNSORTED ? Lightbulb : BRANCH_ICON[summary.key]
  const cosmic =
    summary.key !== UNSORTED && COSMIC_BRANCHES.includes(summary.key)
  return (
    <Button
      variant='outline'
      size='tile'
      aria-pressed={active}
      onClick={onSelect}
      className={cn(
        'flex-col items-stretch',
        active && 'border-primary/60 bg-primary/10'
      )}
    >
      <span className='flex min-w-0 items-center gap-2.5'>
        <Medallion
          icon={Icon}
          tone={cosmic ? 'info' : active ? 'gold' : 'verdigris'}
          size='sm'
        />
        <span className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='semibold' truncate>
            {summary.key === UNSORTED ? 'Unsorted' : humanize(summary.key)}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {`${formatInteger(summary.items.length)} arts · tier ${tierNumeral(summary.top)}`}
          </Muted>
        </span>
        {cosmic && (
          <Badge size='sm' variant='info'>
            <Sparkles />
            Cosmic
          </Badge>
        )}
      </span>
      <Progress
        size='sm'
        tone={cosmic ? 'info' : 'default'}
        value={(summary.top / Math.max(1, peak)) * PERCENT}
        aria-label='Highest tier reached'
      />
    </Button>
  )
}

function LockedTile({ branch }: { branch: KnowledgeBranch }) {
  const Icon = BRANCH_ICON[branch]
  return (
    <div className='flex min-w-0 items-center gap-2.5 rounded-xl border border-dashed bg-muted/40 p-3'>
      <Medallion icon={Icon} tone='muted' size='sm' />
      <span className='flex min-w-0 flex-1 flex-col'>
        <Text as='span' weight='medium' tone='muted' truncate>
          {humanize(branch)}
        </Text>
        <Muted as='span' variant='caption' truncate>
          Not yet discovered
        </Muted>
      </span>
      <Lock aria-hidden='true' className='size-icon-sm text-muted-foreground' />
    </div>
  )
}

function TechDetail({
  item,
  all,
  onSelect,
}: {
  item: KnowledgeView
  all: KnowledgeView[]
  onSelect: (id: number) => void
}) {
  const unlocks = all.filter((other) =>
    other.prerequisites.some((ref) => ref.id === item.knowledge.id)
  )
  const known = new Set(all.map((other) => other.knowledge.id))
  const Icon = item.branch ? BRANCH_ICON[item.branch] : Lightbulb
  const spread = Math.max(0, Math.min(PERCENT, item.spread ?? 0))
  const lost = item.knowers.length === 0
  return (
    <div className='flex min-w-0 flex-col gap-4 rounded-xl border bg-card p-4'>
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={Icon} tone={lost ? 'muted' : 'gold'} />
        <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
          <SectionTitle level={3} truncate={2}>
            {item.knowledge.name}
          </SectionTitle>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Badge size='sm' variant='default'>
              {`Tier ${tierNumeral(tierOf(item))}`}
            </Badge>
            {item.branch && (
              <Badge size='sm' variant='outline'>
                {humanize(item.branch)}
              </Badge>
            )}
            {item.knowledge.subtype && (
              <Badge size='sm' variant='outline'>
                {item.knowledge.subtype}
              </Badge>
            )}
            {lost && (
              <Badge size='sm' variant='warning'>
                Forgotten
              </Badge>
            )}
          </div>
        </div>
      </div>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Label>Spread among its world</Label>
          <Text as='span' weight='semibold'>{`${spread}%`}</Text>
        </div>
        <Progress
          tone={spread >= PERCENT ? 'success' : 'default'}
          value={spread}
          aria-label='Spread'
        />
      </div>
      {item.description && (
        <Muted variant='caption' truncate={4}>
          {item.description}
        </Muted>
      )}
      {item.inventor && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Label>Found by</Label>
          <RefLink node={item.inventor} />
          <Muted as='span' variant='caption'>
            {`in epoch ${item.knowledge.birth_epoch}`}
          </Muted>
        </div>
      )}
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Requires</Label>
        {item.prerequisites.length === 0 ? (
          <Muted variant='caption'>
            A first discovery; nothing comes before it.
          </Muted>
        ) : (
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            {item.prerequisites.map((ref) =>
              known.has(ref.id) ? (
                <Button
                  key={ref.id}
                  size='sm'
                  variant='outline'
                  onClick={() => onSelect(ref.id)}
                >
                  <Lock />
                  {ref.name}
                </Button>
              ) : (
                <Badge key={ref.id} variant='outline'>
                  {ref.name}
                </Badge>
              )
            )}
          </div>
        )}
      </div>
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Unlocks</Label>
        {unlocks.length === 0 ? (
          <Muted variant='caption'>Nothing has grown from it yet.</Muted>
        ) : (
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            {unlocks.map((other) => (
              <Button
                key={other.knowledge.id}
                size='sm'
                variant='outline'
                onClick={() => onSelect(other.knowledge.id)}
              >
                <Unlock />
                {other.knowledge.name}
              </Button>
            ))}
          </div>
        )}
      </div>
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>
          {`Keepers · ${formatInteger(item.knowers.length)}`}
        </Label>
        {lost ? (
          <Muted variant='caption'>Nobody knows it any more.</Muted>
        ) : (
          <div className='flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1'>
            <Users
              aria-hidden='true'
              className='size-icon-sm text-muted-foreground'
            />
            {item.knowers.slice(0, KNOWER_LIMIT).map((ref) => (
              <RefLink key={`${ref.kind}-${ref.id}`} node={ref} />
            ))}
            {item.knowers.length > KNOWER_LIMIT && (
              <Muted as='span' variant='caption'>
                {`and ${item.knowers.length - KNOWER_LIMIT} more`}
              </Muted>
            )}
          </div>
        )}
      </div>
      <EntityLink kind='entity' id={String(item.knowledge.id)}>
        <ExternalLink aria-hidden='true' className='size-icon-sm' />
        Its page
      </EntityLink>
    </div>
  )
}

export function KnowledgeTree({ knowledge }: { knowledge: KnowledgeView[] }) {
  const branches = useMemo(() => {
    const map = new Map<BranchKey, KnowledgeView[]>()
    for (const item of knowledge) {
      const key: BranchKey = item.branch ?? UNSORTED
      map.set(key, [...(map.get(key) ?? []), item])
    }
    const order = (key: BranchKey) =>
      key === UNSORTED ? 2 : COSMIC_BRANCHES.includes(key) ? 1 : 0
    return [...map.entries()]
      .map(([key, items]): BranchSummary => ({
        key,
        items,
        top: Math.max(...items.map(tierOf)),
        keepers: items.reduce((sum, item) => sum + item.knowers.length, 0),
      }))
      .sort(
        (left, right) =>
          order(left.key) - order(right.key) ||
          right.items.length - left.items.length
      )
  }, [knowledge])
  const peak = Math.max(1, ...branches.map((summary) => summary.top))
  const [branch, setBranch] = useState<BranchKey | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const current =
    branches.find((summary) => summary.key === branch) ?? branches[0]
  const chosen =
    current?.items.find((item) => item.knowledge.id === selected) ??
    current?.items.reduce<KnowledgeView | undefined>(
      (best, item) => (!best || tierOf(item) > tierOf(best) ? item : best),
      undefined
    )
  const needle = query.trim().toLowerCase()
  const hits = needle
    ? knowledge
        .filter((item) => item.knowledge.name.toLowerCase().includes(needle))
        .slice(0, SEARCH_LIMIT)
    : []
  const select = (id: number) => {
    const found = knowledge.find((item) => item.knowledge.id === id)
    if (!found) return
    setBranch(found.branch ?? UNSORTED)
    setSelected(id)
  }
  const locked = COSMIC_BRANCHES.filter(
    (key) => !branches.some((summary) => summary.key === key)
  )
  if (knowledge.length === 0 || !current)
    return (
      <EmptyState
        icon={Lightbulb}
        title='No knowledge yet'
        description='Peoples discover agriculture, writing and stranger arts as epochs pass.'
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <Section
        id='knowledge-branches'
        title='Branches of knowledge'
        description='Each branch climbs in tiers; cosmic branches open the ways between worlds.'
        level={3}
        actions={
          <div className='flex min-w-0 flex-col gap-1'>
            <Input
              type='search'
              leadingIcon={Search}
              placeholder='Find an art'
              aria-label='Find an art'
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
        }
      >
        {hits.length > 0 && (
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            {hits.map((item) => (
              <Button
                key={item.knowledge.id}
                size='sm'
                variant='secondary'
                onClick={() => {
                  select(item.knowledge.id)
                  setQuery('')
                }}
              >
                <FlaskConical />
                {item.knowledge.name}
              </Button>
            ))}
          </div>
        )}
        <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4'>
          {branches.map((summary) => (
            <li key={summary.key} className='min-w-0'>
              <BranchTile
                summary={summary}
                peak={peak}
                active={summary.key === current.key}
                onSelect={() => {
                  setBranch(summary.key)
                  setSelected(null)
                }}
              />
            </li>
          ))}
          {locked.map((key) => (
            <li key={key} className='min-w-0'>
              <LockedTile branch={key} />
            </li>
          ))}
        </ul>
      </Section>
      <div className='grid min-w-0 grid-cols-1 gap-6 xl:grid-cols-3'>
        <div className='flex min-w-0 flex-col gap-3 xl:col-span-2'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Text as='span' weight='semibold'>
              {current.key === UNSORTED
                ? 'Unsorted knowledge'
                : `The ${humanize(current.key)} tree`}
            </Text>
            <Badge size='sm' variant='outline'>
              {`${formatInteger(current.items.length)} arts`}
            </Badge>
            <Badge size='sm' variant='outline'>
              {`${formatInteger(current.keepers)} keepings`}
            </Badge>
            <Muted as='span' variant='caption'>
              Lines lead from what is needed to what it opens; dashed arts are
              forgotten; the bar is how far each has spread.
            </Muted>
          </div>
          <TechBoard
            items={current.items}
            selected={chosen?.knowledge.id ?? null}
            onSelect={select}
          />
        </div>
        {chosen && (
          <div className='min-w-0 xl:sticky xl:top-topbar xl:self-start'>
            <TechDetail item={chosen} all={knowledge} onSelect={select} />
          </div>
        )}
      </div>
    </div>
  )
}
