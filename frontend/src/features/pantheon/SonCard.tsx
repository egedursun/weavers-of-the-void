import { type ReactNode } from 'react'
import {
  Footprints,
  Gauge,
  Globe,
  HandHeart,
  Heart,
  Orbit,
  Lock,
  Quote,
  ScrollText,
  Skull,
  Sparkles,
  Star,
  Swords,
  Target,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { type Rarity } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  AttributeTile,
  EntityLink,
  IconStat,
  LevelMeter,
  Portrait,
  RarityBadge,
  StatBar,
} from '@/components/domain'
import { MentionText } from '@/components/domain/MentionText'
import {
  DOMAIN_GLYPH,
  DOMAIN_GLYPH_FALLBACK,
} from '@/components/domain/domainGlyphIcons'
import {
  RARITY_BAR_CLASS,
  RARITY_FRAME_CLASS,
  RARITY_TEXT_CLASS,
  RARITY_WASH_CLASS,
} from '@/components/domain/rarityClasses'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { Label, Muted, Text } from '@/components/typography'
import { HalfTurnChip } from '@/features/son/HalfTurnChip'
import { type SonPublic } from './api'
import { STAT_SCALE } from './constants'
import { useRuleLookup } from './gate'
import { BAND_LABEL, BAND_TONE, STATS, STAT_GROUPS, useLabels } from './labels'
import { mediaUrl } from './media'
import {
  isDead,
  reputationOf,
  starText,
  statValue,
  statusChips,
  xpNeeded,
} from './sonFacts'

type SonCardProps = {
  view: SonPublic
  ready: boolean
  worldName?: string | null
  acting?: boolean
  hints?: string[]
  interactive?: boolean
  actions?: ReactNode
}

function Chip({
  label,
  hint,
  variant,
  icon,
}: {
  label: string
  hint?: string
  variant:
    'default' | 'secondary' | 'destructive' | 'success' | 'warning' | 'outline'
  icon?: ReactNode
}) {
  const badge = (
    <Badge size='sm' variant={variant}>
      {icon}
      {label}
    </Badge>
  )
  if (!hint) return badge
  return (
    <Tooltip>
      <TooltipTrigger asChild>{badge}</TooltipTrigger>
      <TooltipContent>{hint}</TooltipContent>
    </Tooltip>
  )
}

const FOILED: ReadonlySet<Rarity> = new Set(['legendary', 'mythic'])

function Stars({ count, rarity }: { count: number; rarity: Rarity }) {
  if (count <= 0) return <Label>{starText(count)}</Label>
  return (
    <span
      className='flex items-center gap-0.5'
      role='img'
      aria-label={`${count} ${count === 1 ? 'star' : 'stars'}`}
    >
      {Array.from({ length: count }, (_, index) => (
        <Star
          key={index}
          aria-hidden='true'
          className={cn('size-icon-xs fill-current', RARITY_TEXT_CLASS[rarity])}
        />
      ))}
    </span>
  )
}

export function SonCard({
  view,
  ready,
  worldName,
  acting = false,
  hints = [],
  interactive = true,
  actions,
}: SonCardProps) {
  const son = view.son
  const { open } = useDrawerStack()
  const rule = useRuleLookup()
  const { domain } = useLabels()
  const dead = isDead(son)
  const chips = statusChips(view, ready, rule('death.fading_death_epochs'))
  const reputation = reputationOf(view)
  const needed = xpNeeded(son.level, rule('core_rules.xp_per_level'))
  const card = view.card
  const PrimaryGlyph = DOMAIN_GLYPH[son.domain_primary] ?? DOMAIN_GLYPH_FALLBACK
  const SecondaryGlyph =
    DOMAIN_GLYPH[son.domain_secondary] ?? DOMAIN_GLYPH_FALLBACK
  return (
    <Card
      data-son-card={son.id}
      data-rarity={son.rarity}
      aria-busy={acting || undefined}
      className={cn(
        'relative h-full overflow-hidden',
        RARITY_FRAME_CLASS[son.rarity],
        FOILED.has(son.rarity) && !dead && 'card-foil',
        interactive &&
          'cursor-pointer transition-all hover:-translate-y-0.5 hover:border-primary/60 hover:shadow-xl',
        dead && 'opacity-70 grayscale-50',
        acting && 'border-primary'
      )}
      onClick={(event) => {
        if (!interactive) return
        const target = event.target as HTMLElement
        if (target.closest('a,button,input,[role="checkbox"]')) return
        open({ kind: 'son', id: String(son.id) })
      }}
    >
      <span
        aria-hidden='true'
        className={cn(
          'pointer-events-none absolute inset-x-0 top-0 h-1',
          RARITY_BAR_CLASS[son.rarity]
        )}
      />
      <span
        aria-hidden='true'
        className={cn(
          'pointer-events-none absolute inset-x-0 top-0 h-40 bg-linear-to-b to-transparent',
          RARITY_WASH_CLASS[son.rarity]
        )}
      />
      <CardHeader className='relative'>
        <div className='flex min-w-0 items-start gap-3'>
          <Portrait
            name={son.name}
            src={mediaUrl(view.cover)}
            size='lg'
            shape='square'
            rarity={son.rarity}
          />
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
              <RarityBadge rarity={son.rarity} size='sm' />
              <Stars count={son.stars} rarity={son.rarity} />
            </div>
            {interactive ? (
              <EntityLink kind='son' id={String(son.id)} rarity={son.rarity}>
                {dead ? `† ${son.name}` : son.name}
              </EntityLink>
            ) : (
              <Text weight='semibold' truncate className='font-display'>
                {son.name}
              </Text>
            )}
            <Muted variant='caption' truncate={2}>
              {son.title}
            </Muted>
          </div>
        </div>
      </CardHeader>
      <CardContent className='flex flex-col gap-4'>
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Chip
            variant='default'
            icon={<PrimaryGlyph />}
            label={domain(son.domain_primary)}
            hint='Primary domain'
          />
          <Chip
            variant='outline'
            icon={<SecondaryGlyph />}
            label={domain(son.domain_secondary)}
            hint='Secondary domain'
          />
          {chips.map((chip) => (
            <Chip
              key={chip.key}
              label={chip.label}
              variant={chip.variant}
              hint={chip.hint}
            />
          ))}
          {reputation && !dead && (
            <Chip
              variant='outline'
              label={`Sees father: ${reputation}`}
              hint={
                son.reputation_love !== null
                  ? `Love ${son.reputation_love} · fear ${son.reputation_fear ?? 0} · forgotten ${son.reputation_forgotten ?? 0}`
                  : undefined
              }
            />
          )}
          {worldName && (
            <Chip variant='outline' label={worldName} icon={<Globe />} />
          )}
          <HalfTurnChip view={view} />
        </div>
        {(card.last_words ||
          card.last_action ||
          card.best_friend ||
          card.worst_rival) && (
          <div className='flex min-w-0 flex-col gap-1.5'>
            {card.last_words && (
              <Text variant='caption' italic truncate={2}>
                <Quote aria-hidden='true' className='inline size-icon-xs' />{' '}
                {card.last_words}
              </Text>
            )}
            {card.last_action && (
              <Muted variant='caption' truncate={2}>
                {card.last_action_epoch !== null &&
                  `Epoch ${card.last_action_epoch}: `}
                <MentionText text={card.last_action} />
              </Muted>
            )}
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              {card.best_friend && (
                <Chip
                  variant='success'
                  icon={<Heart />}
                  label={`${card.best_friend.name} +${card.best_friend.value}`}
                  hint={`Closest sibling: ${card.best_friend.name} (+${card.best_friend.value})`}
                />
              )}
              {card.worst_rival && (
                <Chip
                  variant='destructive'
                  icon={<Swords />}
                  label={`${card.worst_rival.name} ${card.worst_rival.value}`}
                  hint={`Nemesis: ${card.worst_rival.name} (${card.worst_rival.value})`}
                />
              )}
            </div>
          </div>
        )}
        <div className='grid min-w-0 grid-cols-1 gap-2'>
          <StatBar
            label='Life'
            icon={Heart}
            value={son.hp}
            max={view.max_hp}
            tone='destructive'
          />
          <StatBar
            label='Essence'
            icon={Sparkles}
            value={son.essence}
            max={view.max_essence}
          />
          <StatBar
            label={`Existence · ${BAND_LABEL[view.band]}`}
            icon={Orbit}
            value={son.existence}
            max={STAT_SCALE}
            tone={BAND_TONE[view.band]}
          />
        </div>
        <div className='grid min-w-0 grid-cols-3 gap-2'>
          {STAT_GROUPS.map((group) => (
            <div key={group} className='flex min-w-0 flex-col gap-1.5'>
              <Label variant='overline' truncate>
                {group}
              </Label>
              {STATS.filter((stat) => stat.group === group).map((stat) => (
                <AttributeTile
                  key={stat.key}
                  abbr={stat.abbr}
                  label={stat.label}
                  hint={stat.effect}
                  icon={stat.icon}
                  value={statValue(son, stat.key)}
                  max={STAT_SCALE}
                  tone={son.rarity}
                />
              ))}
            </div>
          ))}
        </div>
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          {view.powers.map((power, index) => {
            const locked = index >= view.unlocked_powers
            return (
              <Chip
                key={power.slot}
                variant={locked ? 'secondary' : 'default'}
                icon={locked ? <Lock /> : <Sparkles />}
                label={power.name}
                hint={
                  locked
                    ? `${power.description} (not yet unlocked)`
                    : power.description
                }
              />
            )
          })}
          {view.powers.length === 0 && (
            <Chip
              variant='secondary'
              icon={<Lock />}
              label='No power awakened'
            />
          )}
        </div>
        {(son.standing_order || son.plan) && (
          <Text variant='caption' truncate={3}>
            <ScrollText aria-hidden='true' className='inline size-icon-xs' />{' '}
            {son.standing_order
              ? `Order: ${son.standing_order}`
              : son.plan_epoch !== null && son.plan_epoch !== undefined
                ? `Plan (Epoch ${son.plan_epoch}): ${son.plan}`
                : `Plan: ${son.plan}`}
          </Text>
        )}
        {!dead && hints.length > 0 && (
          <div className='flex min-w-0 flex-col gap-1'>
            <Label variant='overline'>
              {hints.length > 1
                ? `Opportunities · ${hints.length}`
                : 'Opportunity'}
            </Label>
            <Text variant='caption' truncate={2}>
              <Target aria-hidden='true' className='inline size-icon-xs' />{' '}
              {hints[0]}
            </Text>
          </div>
        )}
      </CardContent>
      <CardFooter className='mt-auto flex-col items-stretch gap-3 border-t'>
        <LevelMeter level={son.level} xp={son.xp} needed={needed} />
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <IconStat
            icon={HandHeart}
            tone='gold'
            label='Faith'
            hint='Worship gathered from mortals'
            value={son.faith}
          />
          <IconStat
            icon={Star}
            tone='warning'
            label='Fame'
            hint='How widely the deeds are known'
            value={son.fame}
          />
          <IconStat
            icon={Footprints}
            tone='info'
            label='Actions'
            hint='Actions left this epoch'
            value={view.action_points}
          />
          <IconStat
            icon={Gauge}
            tone='verdigris'
            label='Power cap'
            hint='Highest power a creation can reach'
            value={view.power_cap}
          />
          {dead && (
            <Skull
              aria-hidden='true'
              className='size-icon-sm text-destructive'
            />
          )}
          {actions && (
            <div className='ml-auto flex items-center gap-1.5'>{actions}</div>
          )}
        </div>
      </CardFooter>
    </Card>
  )
}
