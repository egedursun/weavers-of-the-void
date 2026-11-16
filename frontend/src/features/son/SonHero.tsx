import { useState } from 'react'
import {
  Anchor,
  Baby,
  Bookmark,
  BookmarkCheck,
  Footprints,
  Gauge,
  Globe,
  HandHeart,
  Heart,
  Orbit,
  Printer,
  Sparkles,
  Star,
  UserRound,
} from 'lucide-react'
import { formatDecimal } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EntityLink,
  HeroFrame,
  LevelMeter,
  MiniStat,
  Paged,
  RarityBadge,
} from '@/components/domain'
import { MentionText } from '@/components/domain/MentionText'
import { RecordNavLink } from '@/components/domain/RecordNavLink'
import { Label, Muted, PageTitle, Text } from '@/components/typography'
import { NamedRecord } from '@/features/entity/NamedRecord'
import { PortraitGenerateOverlay } from '@/features/images/PortraitGenerateOverlay'
import { type SonPublic, useWorldState } from '@/features/pantheon/api'
import { useRuleLookup } from '@/features/pantheon/gate'
import { BAND_LABEL, BAND_TONE, useLabels } from '@/features/pantheon/labels'
import { fadingLeft, starText, xpNeeded } from '@/features/pantheon/sonFacts'
import { HalfTurnChip } from './HalfTurnChip'
import { type SonDetail } from './api'
import { isBookmarked, toggleBookmark } from './bookmarks'

export function SonHero({
  view,
  detail,
}: {
  view: SonPublic
  detail: SonDetail
}) {
  const son = view.son
  const { domain } = useLabels()
  const rule = useRuleLookup()
  const state = useWorldState()
  const [marked, setMarked] = useState(() => isBookmarked('son', son.id))
  const dead = son.status === 'dead'
  const world = state.data?.worlds.find(
    (item) => item.id === son.current_world_id
  )
  const left = fadingLeft(son, rule('death.fading_death_epochs'))
  const needed = xpNeeded(son.level, rule('core_rules.xp_per_level'))
  const staleAfter = rule('context.plan_stale_epochs')
  const epochNow = state.data?.world?.epoch
  const stale =
    son.plan_epoch !== null &&
    son.plan_epoch !== undefined &&
    staleAfter !== undefined &&
    epochNow !== undefined &&
    epochNow - son.plan_epoch >= staleAfter
  return (
    <HeroFrame>
      <header className='flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start'>
        <PortraitGenerateOverlay
          nodeId={son.id}
          name={son.name}
          cover={view.cover ?? null}
          rarity={son.rarity}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-2'>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <RarityBadge rarity={son.rarity} size='sm' />
            <Label>{starText(son.stars)}</Label>
            {dead && son.death_epoch !== null && (
              <Label>{`Died in Epoch ${son.death_epoch}`}</Label>
            )}
            {son.reputation_last_contact_epoch !== null && (
              <Label>{`You last spoke to it in Epoch ${son.reputation_last_contact_epoch}`}</Label>
            )}
            {son.reputation_unanswered !== null &&
              son.reputation_unanswered > 0 && (
                <Label>{`${son.reputation_unanswered} of its prayers wait for your answer`}</Label>
              )}
          </div>
          <PageTitle truncate={2}>
            {dead ? `† ${son.name}` : son.name}
          </PageTitle>
          <Muted>{son.title}</Muted>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Badge size='sm' variant='outline'>
              {domain(son.domain_primary)}
            </Badge>
            <Badge size='sm' variant='outline'>
              {domain(son.domain_secondary)}
            </Badge>
            {world && (
              <Badge size='sm' variant='info'>
                <Globe />
                {world.name}
              </Badge>
            )}
            <HalfTurnChip view={view} />
            {left !== null && (
              <Badge
                size='sm'
                variant='destructive'
              >{`Being forgotten · fades in ${plural(left, 'epoch', 'epochs')}`}</Badge>
            )}
          </div>
          <LevelMeter level={son.level} xp={son.xp} needed={needed} />
          <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
            <MiniStat
              icon={Heart}
              tone='danger'
              label='Life'
              value={`${son.hp}/${view.max_hp}`}
            />
            <MiniStat
              icon={Sparkles}
              tone='verdigris'
              label='Essence'
              value={`${son.essence}/${view.max_essence}`}
            />
            <MiniStat
              icon={HandHeart}
              tone='gold'
              label='Faith'
              value={formatDecimal(detail.live_faith, 1)}
            />
            <MiniStat
              icon={Star}
              tone='warning'
              label='Fame'
              value={son.fame}
            />
            <MiniStat
              icon={Orbit}
              tone={
                BAND_TONE[view.band] === 'destructive'
                  ? 'danger'
                  : BAND_TONE[view.band] === 'warning'
                    ? 'warning'
                    : BAND_TONE[view.band] === 'success'
                      ? 'success'
                      : 'info'
              }
              label={view.band_label || BAND_LABEL[view.band]}
              value={son.existence}
              hint='Existence: worship, memory and a living anchor feed it.'
            />
            <MiniStat
              icon={Footprints}
              tone='info'
              label='Actions'
              value={view.action_points}
            />
            <MiniStat
              icon={Gauge}
              tone='verdigris'
              label='Power cap'
              value={view.power_cap}
            />
          </div>
          {(detail.anchor ||
            detail.parent ||
            son.co_parent_son_id !== null ||
            son.corpse_entity_id !== null ||
            detail.children.length > 0) && (
            <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
              {detail.anchor && (
                <Badge size='sm' variant='outline'>
                  <Anchor />
                  Anchor
                  <EntityLink kind='entity' id={String(detail.anchor.id)}>
                    {detail.anchor.name}
                  </EntityLink>
                </Badge>
              )}
              {detail.parent && (
                <Badge size='sm' variant='outline'>
                  <UserRound />
                  Parent
                  <EntityLink kind='son' id={String(detail.parent.id)}>
                    {detail.parent.name}
                  </EntityLink>
                </Badge>
              )}
              {son.co_parent_son_id !== null && (
                <Badge size='sm' variant='outline'>
                  <UserRound />
                  Second parent
                  <NamedRecord
                    id={son.co_parent_son_id}
                    fallback='a lost son'
                  />
                </Badge>
              )}
              {son.corpse_entity_id !== null && (
                <Badge size='sm' variant='outline'>
                  <Anchor />
                  Body
                  <NamedRecord id={son.corpse_entity_id} fallback='lost' />
                </Badge>
              )}
              <Paged items={detail.children}>
                {(child) => (
                  <Badge key={child.id} size='sm' variant='outline'>
                    <Baby />
                    Child
                    <EntityLink kind='son' id={String(child.id)}>
                      {child.name}
                    </EntityLink>
                  </Badge>
                )}
              </Paged>
            </div>
          )}
          {son.plan && (
            <div className='flex min-w-0 flex-col gap-1.5 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'>
              <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                <Label variant='overline'>Plan</Label>
                {son.plan_epoch !== null && son.plan_epoch !== undefined && (
                  <Badge
                    size='sm'
                    variant='outline'
                  >{`Written in Epoch ${son.plan_epoch}`}</Badge>
                )}
                {stale && (
                  <Badge size='sm' variant='warning'>
                    Stale
                  </Badge>
                )}
              </div>
              <Text italic>
                <MentionText text={son.plan} />
              </Text>
            </div>
          )}
          <div className='flex min-w-0 flex-wrap gap-2'>
            <RecordNavLink to={{ view: 'network', focus: son.id }} />
            {son.current_world_id !== null && (
              <RecordNavLink
                to={{ view: 'world-map', world: son.current_world_id }}
              />
            )}
            <RecordNavLink to={{ view: 'chronicle', epoch: son.birth_epoch }} />
            {son.current_world_id !== null && (
              <RecordNavLink
                to={{ view: 'climate', world: son.current_world_id }}
              />
            )}
            <Button variant='outline' size='sm' asChild>
              <a
                href={`/api/book?son_id=${son.id}`}
                target='_blank'
                rel='noreferrer'
              >
                <Printer />
                Print page
              </a>
            </Button>
            <Button
              variant={marked ? 'secondary' : 'outline'}
              size='sm'
              aria-pressed={marked}
              onClick={() => setMarked(toggleBookmark('son', son.id))}
            >
              {marked ? <BookmarkCheck /> : <Bookmark />}
              {marked ? 'Bookmarked' : 'Bookmark'}
            </Button>
          </div>
        </div>
      </header>
    </HeroFrame>
  )
}
