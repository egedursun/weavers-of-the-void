import { useEffect, useState } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  Download,
  ExternalLink,
  Gem,
  Globe2,
  type LucideIcon,
  Package,
  PackageOpen,
  Repeat2,
  ScrollText,
  Skull,
  Sparkles,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import { type ProgressTone } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  DomainGlyph,
  ExpandableText,
  HeroFrame,
  type KpiTone,
  KeyValueList,
  LevelMeter,
  Medallion,
  MiniStat,
  PagedList,
  PanelGrid,
  RarityBadge,
  Section,
  StatBar,
} from '@/components/domain'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { Label, Muted, PageTitle, Stat, Text } from '@/components/typography'
import { GenerateImageButton } from '@/features/images/GenerateImageButton'
import { useRuleLookup } from '@/features/pantheon/gate'
import { useLabels } from '@/features/pantheon/labels'
import { xpNeeded } from '@/features/pantheon/sonFacts'
import { LoreCard } from './LoreCard'
import { PackOpening } from './PackOpening'
import { type CharacterCard, type CharacterCardStat } from './api'
import {
  type CardSide,
  FRAME_ICON,
  STAT_GROUP_ICON,
  type StatGroupKey,
  drawerOf,
  frameOf,
  isDivine,
  kindLabel,
  rarityHint,
  statGroups,
  statMeta,
  statText,
  tierLabel,
} from './cardModel'
import { sealedIn, useCardSeals } from './sealStore'

const INSPECT_ART_WIDTH = 960
const POWERS_SHOWN = 4
const PREFETCH_AHEAD = 4
const DOMAINS_SHOWN = 4

const VITAL_TONE: Record<string, KpiTone> = {
  hp: 'danger',
  essence: 'verdigris',
  existence: 'info',
  faith: 'gold',
  fame: 'warning',
  power: 'gold',
}

const BAR_TONE: Record<string, ProgressTone> = {
  hp: 'destructive',
  essence: 'verdigris',
  existence: 'info',
  power: 'warning',
}

type CardInspectorProps = {
  visible: CharacterCard[]
  index: number | null
  total: number
  onIndex: (index: number | null) => void
  hasMore: boolean
  loadingMore: boolean
  onLoadMore: () => void
  onDownload: (card: CharacterCard, side: CardSide) => void
  downloadReason: string | null
  worldOf: (card: CharacterCard) => string | null
}

function measured(stat: CharacterCardStat): stat is CharacterCardStat & {
  maximum: number
} {
  return stat.maximum !== null && stat.maximum > 0 && stat.value >= 0
}

function GroupPanel({
  group,
  stats,
  tone,
  wide,
  divine,
}: {
  group: StatGroupKey
  stats: CharacterCardStat[]
  tone: ProgressTone
  wide: boolean
  divine: boolean
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={STAT_GROUP_ICON[group]} size='sm' />
        <Label variant='overline'>{group}</Label>
      </div>
      <div
        className={cn(
          'grid min-w-0 grid-cols-1 gap-3',
          wide && 'sm:grid-cols-2 lg:grid-cols-3'
        )}
      >
        {stats.map((stat) => {
          const meta = statMeta(stat, divine)
          return (
            <div key={stat.key} className='flex min-w-0 flex-col gap-1'>
              <div className='flex min-w-0 flex-1 flex-col justify-center rounded-md border surface-sheen border-gild/60 bg-card p-2.5'>
                {measured(stat) ? (
                  <StatBar
                    label={stat.label}
                    icon={meta.icon}
                    value={stat.value}
                    max={stat.maximum}
                    tone={BAR_TONE[stat.key] ?? tone}
                    showMax={stat.key === 'hp' || stat.key === 'essence'}
                  />
                ) : (
                  <div className='flex min-w-0 items-center gap-2'>
                    <meta.icon
                      aria-hidden='true'
                      className='size-icon-sm shrink-0 text-muted-foreground'
                    />
                    <Label truncate className='flex-1'>
                      {stat.label}
                    </Label>
                    <Stat value={stat.value} />
                  </div>
                )}
              </div>
              {meta.effect && (
                <Muted variant='caption' truncate={2}>
                  {meta.effect}
                </Muted>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function HeroValue({ stat }: { stat: CharacterCardStat }) {
  return (
    <MiniStat
      icon={statMeta(stat, false).icon}
      label={stat.label}
      value={statText(stat)}
      tone={VITAL_TONE[stat.key] ?? 'gold'}
      hint={
        stat.maximum !== null
          ? `${stat.label} ${formatInteger(stat.value)} of ${formatInteger(stat.maximum)}`
          : undefined
      }
    />
  )
}

function Walker({
  index,
  total,
  atFirst,
  nextReason,
  onStep,
}: {
  index: number
  total: number
  atFirst: boolean
  nextReason: string | null
  onStep: (delta: number) => void
}) {
  return (
    <div className='flex min-w-0 items-center gap-2'>
      <Button
        variant='outline'
        size='icon'
        aria-label='Previous card'
        onClick={() => onStep(-1)}
        disabled={atFirst}
        disabledReason='This is the first card shown.'
      >
        <ChevronLeft />
      </Button>
      <Label>{`${formatInteger(index + 1)} / ${formatInteger(total)}`}</Label>
      <Button
        variant='outline'
        size='icon'
        aria-label='Next card'
        onClick={() => onStep(1)}
        disabled={nextReason !== null}
        disabledReason={nextReason ?? undefined}
      >
        <ChevronRight />
      </Button>
    </div>
  )
}

function KindBadge({
  card,
  icon: Icon,
}: {
  card: CharacterCard
  icon: LucideIcon
}) {
  const { entityType } = useLabels()
  return (
    <Badge variant='secondary' size='sm'>
      <Icon />
      {kindLabel(card, entityType)}
    </Badge>
  )
}

export function CardInspector({
  visible,
  index,
  total,
  onIndex,
  hasMore,
  loadingMore,
  onLoadMore,
  onDownload,
  downloadReason,
  worldOf,
}: CardInspectorProps) {
  const [flipped, setFlipped] = useState(false)
  const [unveiled, setUnveiled] = useState<number | null>(null)
  const seals = useCardSeals()
  const drawers = useDrawerStack()
  const rule = useRuleLookup()
  const { domain, entityType } = useLabels()
  const card = index === null ? undefined : visible[index]
  useEffect(() => {
    if (
      index !== null &&
      hasMore &&
      !loadingMore &&
      index >= visible.length - PREFETCH_AHEAD
    )
      onLoadMore()
  }, [index, hasMore, loadingMore, visible.length, onLoadMore])
  const atLast = index !== null && index >= visible.length - 1
  const step = (delta: number) => {
    if (index === null) return
    const next = index + delta
    if (next >= visible.length && hasMore && !loadingMore) onLoadMore()
    if (next < 0 || next >= visible.length) return
    setFlipped(false)
    setUnveiled(null)
    onIndex(next)
  }
  const close = () => {
    setFlipped(false)
    setUnveiled(null)
    onIndex(null)
  }
  const sealed = card ? sealedIn(seals, card.node_id) : false
  const staged = card !== undefined && (sealed || unveiled === card.node_id)
  const nextSealed =
    index === null
      ? -1
      : visible.findIndex(
          (item, position) => position > index && sealedIn(seals, item.node_id)
        )
  const nextReason =
    atLast && (!hasMore || loadingMore)
      ? hasMore
        ? 'The next cards are being drawn.'
        : 'This is the last card of the deck.'
      : null
  const flip = () => setFlipped((value) => !value)
  const worldName = card ? worldOf(card) : null
  const groups = card
    ? statGroups(card).filter((entry) => entry.group !== 'Vitals')
    : []
  const heroValues = card
    ? [
        ...card.headline,
        ...card.stats.filter(
          (stat) =>
            statMeta(stat, true).group === 'Vitals' &&
            !card.headline.some((line) => line.key === stat.key)
        ),
      ]
    : []
  const needed =
    card && card.level !== null
      ? xpNeeded(card.level, rule('core_rules.xp_per_level'))
      : null
  return (
    <Dialog open={card !== undefined} onOpenChange={(open) => !open && close()}>
      <DialogContent
        className='sm:max-w-6xl'
        onOpenAutoFocus={(event) => event.preventDefault()}
        onKeyDown={(event) => {
          if (event.key === 'ArrowRight') step(1)
          else if (event.key === 'ArrowLeft') step(-1)
          else if (event.key.toLowerCase() === 'f' && !staged) flip()
        }}
      >
        {card && staged && (
          <div className='flex min-w-0 flex-col gap-4'>
            <div className='flex min-w-0 flex-wrap items-center justify-between gap-3 pe-8'>
              <div className='flex min-w-0 flex-col gap-1'>
                <DialogTitle asChild>
                  <PageTitle truncate>
                    {unveiled === card.node_id ? card.name : 'A sealed pack'}
                  </PageTitle>
                </DialogTitle>
                <DialogDescription asChild>
                  <Muted>
                    {unveiled === card.node_id
                      ? 'The pack is open and the card is yours to read.'
                      : 'Swipe across the seal or tap the pack to see whose card waits inside.'}
                  </Muted>
                </DialogDescription>
              </div>
              <Walker
                index={index ?? 0}
                total={total}
                atFirst={index === 0}
                nextReason={nextReason}
                onStep={step}
              />
            </div>
            <PackOpening
              key={card.node_id}
              card={card}
              onRevealed={() => {
                setUnveiled(card.node_id)
                seals.open(card.node_id)
              }}
            >
              {unveiled === card.node_id && (
                <>
                  <Button variant='outline' onClick={() => setUnveiled(null)}>
                    <Gem />
                    Read the whole card
                  </Button>
                  <Button
                    onClick={() => {
                      setFlipped(false)
                      setUnveiled(null)
                      onIndex(nextSealed)
                    }}
                    disabled={nextSealed < 0}
                    disabledReason='No sealed pack is left among the cards shown.'
                  >
                    <PackageOpen />
                    Open the next pack
                  </Button>
                </>
              )}
            </PackOpening>
          </div>
        )}
        {card && !staged && (
          <div className='flex min-w-0 flex-col gap-6'>
            <HeroFrame>
              <div className='flex min-w-0 flex-col items-center gap-6 md:flex-row md:items-start'>
                <div className='flex w-full max-w-64 shrink-0 flex-col items-center gap-3'>
                  <LoreCard
                    card={card}
                    flipped={flipped}
                    artWidth={INSPECT_ART_WIDTH}
                    role='button'
                    tabIndex={0}
                    aria-label={
                      flipped
                        ? 'Show the front of the card'
                        : 'Turn the card over'
                    }
                    onClick={flip}
                    onKeyDown={(event) => {
                      if (event.key !== 'Enter' && event.key !== ' ') return
                      event.preventDefault()
                      flip()
                    }}
                  />
                  <Walker
                    index={index ?? 0}
                    total={total}
                    atFirst={index === 0}
                    nextReason={nextReason}
                    onStep={step}
                  />
                </div>
                <div className='flex min-w-0 flex-1 flex-col gap-3'>
                  <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span tabIndex={0} className='inline-flex rounded-md'>
                          {card.rarity ? (
                            <RarityBadge rarity={card.rarity} size='sm' />
                          ) : (
                            <Badge variant='outline' size='sm'>
                              {tierLabel(card)}
                            </Badge>
                          )}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>{rarityHint(card)}</TooltipContent>
                    </Tooltip>
                    <KindBadge card={card} icon={FRAME_ICON[frameOf(card)]} />
                    {card.stars !== null && (
                      <Label>{`${card.stars} ${card.stars === 1 ? 'star' : 'stars'}`}</Label>
                    )}
                    {card.power_level !== null && (
                      <Label>{`Power level ${card.power_level}`}</Label>
                    )}
                  </div>
                  <DialogTitle asChild>
                    <PageTitle truncate={2}>
                      {card.fallen ? `† ${card.name}` : card.name}
                    </PageTitle>
                  </DialogTitle>
                  <DialogDescription asChild>
                    <Muted>
                      {card.title ??
                        card.subtype ??
                        kindLabel(card, entityType)}
                    </Muted>
                  </DialogDescription>
                  <div className='flex min-w-0 flex-wrap items-start gap-1.5'>
                    {card.domains.length > 0 && (
                      <PagedList
                        items={card.domains}
                        initial={DOMAINS_SHOWN}
                        noun={['domain', 'domains']}
                        as='div'
                        className='flex min-w-0 flex-wrap gap-1.5'
                        itemKey={(key) => key}
                      >
                        {(key) => (
                          <Badge variant='outline' size='sm'>
                            <DomainGlyph domain={key} />
                            {domain(key)}
                          </Badge>
                        )}
                      </PagedList>
                    )}
                    {card.subtype && card.title && (
                      <Badge variant='outline' size='sm'>
                        {card.subtype}
                      </Badge>
                    )}
                    {worldName && (
                      <Badge variant='info' size='sm'>
                        <Globe2 />
                        {worldName}
                      </Badge>
                    )}
                    {card.born_epoch !== null && (
                      <Badge variant='outline' size='sm'>
                        <Clock />
                        {`Born in epoch ${card.born_epoch}`}
                      </Badge>
                    )}
                    {card.ended_epoch !== null && (
                      <Badge variant='destructive' size='sm'>
                        <Skull />
                        {`Fell in epoch ${card.ended_epoch}`}
                      </Badge>
                    )}
                  </div>
                  {card.level !== null && card.xp !== null && (
                    <LevelMeter
                      level={card.level}
                      xp={card.xp}
                      needed={needed}
                    />
                  )}
                  {heroValues.length > 0 && (
                    <div
                      className={cn(
                        'grid min-w-0 grid-cols-2 gap-2',
                        heroValues.length > 2 && 'sm:grid-cols-3'
                      )}
                    >
                      {heroValues.map((stat) => (
                        <HeroValue key={stat.key} stat={stat} />
                      ))}
                    </div>
                  )}
                  {card.flavor && (
                    <ExpandableText lines={3} italic>
                      {card.flavor}
                    </ExpandableText>
                  )}
                  <div className='flex min-w-0 flex-wrap items-center gap-2'>
                    <Button
                      onClick={() => {
                        close()
                        drawers.open(drawerOf(card))
                      }}
                    >
                      <ExternalLink />
                      Open the page
                    </Button>
                    <Button variant='outline' onClick={flip}>
                      <Repeat2 />
                      {flipped ? 'Show the front' : 'Turn over'}
                    </Button>
                    <Button
                      variant='outline'
                      onClick={() => onDownload(card, 'front')}
                      disabled={downloadReason !== null}
                      disabledReason={downloadReason ?? undefined}
                    >
                      <Download />
                      Save the front
                    </Button>
                    <Button
                      variant='outline'
                      onClick={() => onDownload(card, 'back')}
                      disabled={downloadReason !== null}
                      disabledReason={downloadReason ?? undefined}
                    >
                      <Download />
                      Save the back
                    </Button>
                    <Button
                      variant='outline'
                      onClick={() => {
                        setFlipped(false)
                        seals.seal(card.node_id)
                      }}
                    >
                      <Package />
                      Seal it back in its pack
                    </Button>
                    <GenerateImageButton
                      nodeId={card.node_id}
                      hasImages={card.cover !== null}
                    />
                  </div>
                </div>
              </div>
            </HeroFrame>
            <Section
              title='Every value'
              icon={Gem}
              level={3}
              surface='card'
              description='Every value this soul is measured by, grouped the way the pantheon reads it.'
            >
              {groups.length === 0 ? (
                <Muted>No measured values.</Muted>
              ) : (
                <div
                  className={cn(
                    'grid min-w-0 grid-cols-1 gap-3',
                    groups.length > 1 && 'md:grid-cols-3'
                  )}
                >
                  {groups.map((entry) => (
                    <GroupPanel
                      key={entry.group}
                      group={entry.group}
                      stats={entry.stats}
                      tone={card.rarity ?? 'default'}
                      wide={groups.length === 1}
                      divine={isDivine(card)}
                    />
                  ))}
                </div>
              )}
            </Section>
            <PanelGrid>
              <Section
                title={
                  card.abilities.length > 0
                    ? `Powers · ${formatInteger(card.abilities.length)}`
                    : 'Powers'
                }
                icon={Sparkles}
                level={3}
                surface='card'
                stretch
              >
                {card.abilities.length === 0 ? (
                  <Muted>No power has awakened.</Muted>
                ) : (
                  <PagedList
                    items={card.abilities}
                    initial={POWERS_SHOWN}
                    noun={['power', 'powers']}
                    as='div'
                    className='flex min-w-0 flex-col gap-2'
                    itemKey={(ability, position) =>
                      `${position}-${ability.name}`
                    }
                  >
                    {(ability) => (
                      <div className='flex min-w-0 items-start gap-3 rounded-md border surface-sheen border-gild/60 bg-card p-3'>
                        <Medallion icon={Sparkles} size='sm' tone='verdigris' />
                        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
                          <Text weight='semibold'>{ability.name}</Text>
                          <Muted variant='caption'>{ability.text}</Muted>
                        </div>
                      </div>
                    )}
                  </PagedList>
                )}
              </Section>
              <Section
                title='Nature'
                icon={ScrollText}
                level={3}
                surface='card'
                stretch
              >
                {card.notes.length === 0 ? (
                  <Muted>
                    No nature has been written for this soul. Open the page to
                    write or deepen it.
                  </Muted>
                ) : (
                  <KeyValueList
                    layout='stacked'
                    items={card.notes.map((note) => ({
                      key: note.label,
                      label: note.label,
                      value: note.text,
                    }))}
                  />
                )}
              </Section>
            </PanelGrid>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
