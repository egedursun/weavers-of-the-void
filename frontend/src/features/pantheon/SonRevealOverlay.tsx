import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { APP_NAME } from '@/config/brand'
import { useEvent } from '@/realtime'
import { Crown, FastForward, Sparkles, Star, X } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import {
  RARITIES,
  RARITY_LABEL,
  type Rarity,
  isRarity,
} from '@/constants/rarity'
import { Button } from '@/components/ui/button'
import {
  StageDialog,
  StageDialogContent,
  StageDialogDescription,
  StageDialogTitle,
} from '@/components/ui/stage-dialog'
import { RarityIcon } from '@/components/domain'
import {
  RARITY_BORDER_CLASS,
  RARITY_TEXT_CLASS,
} from '@/components/domain/rarityClasses'
import { Logo } from '@/components/layout/Logo'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import {
  Label,
  Muted,
  PageTitle,
  SectionTitle,
  Text,
} from '@/components/typography'
import { SonCard } from './SonCard'
import { type SonPublic, godKeys, useSons, useWorldState } from './api'
import { type RevealItem, type RevealKind, useRevealQueue } from './revealStore'

const SPARK_COUNT = 16
const CHARGE_MS: Record<Rarity, number> = {
  common: 700,
  uncommon: 900,
  rare: 1200,
  epic: 1600,
  legendary: 2100,
  mythic: 2600,
}
const SHAKING: ReadonlySet<Rarity> = new Set(['legendary', 'mythic'])

const KIND_LABEL: Record<RevealKind, string> = {
  new: 'A new son arrives',
  ascended: 'Ascension',
  genesis: 'Born of genesis',
  preview: 'Reveal preview',
}

const SEALED_TEXT: Record<RevealKind, string> = {
  new: 'Something stirs in the void',
  ascended: 'His light is changing',
  genesis: 'Your first sons wake',
  preview: 'Something stirs in the void',
}

function tierOf(rarity: Rarity): number {
  return RARITIES.indexOf(rarity) + 1
}

function CardBack({
  rarity,
  kind,
  charging,
  onReveal,
}: {
  rarity: Rarity
  kind: RevealKind
  charging: boolean
  onReveal: () => void
}) {
  return (
    <Button
      variant='ghost'
      size='card'
      aria-label='Reveal the son'
      onClick={onReveal}
      className={cn(
        'reveal-face items-center justify-center gap-5 border-2 bg-linear-to-b from-brand-night via-background to-brand-ink text-center shadow-2xl hover:bg-transparent',
        RARITY_BORDER_CLASS[rarity]
      )}
    >
      <span
        className={cn(
          'flex flex-col items-center gap-5',
          charging && SHAKING.has(rarity) && 'reveal-charge'
        )}
      >
        <span className='relative flex h-48 w-48 items-center justify-center'>
          <span
            aria-hidden='true'
            className={cn(
              'reveal-glow rounded-full',
              RARITY_TEXT_CLASS[rarity]
            )}
          />
          <span className='relative flex h-40 w-40 items-center justify-center'>
            <Logo size='md' className='size-full drop-shadow-xl' />
          </span>
        </span>
        <Text as='span' weight='semibold' className='font-brand text-primary'>
          {APP_NAME}
        </Text>
        <span className='flex items-center gap-1.5' aria-hidden='true'>
          {Array.from({ length: tierOf(rarity) }, (_, index) => (
            <Sparkles
              key={index}
              className={cn('size-icon-sm', RARITY_TEXT_CLASS[rarity])}
            />
          ))}
        </span>
        <Muted as='span' variant='caption'>
          {`${SEALED_TEXT[kind]} · tap to reveal`}
        </Muted>
      </span>
    </Button>
  )
}

function Effects({ rarity, open }: { rarity: Rarity; open: boolean }) {
  return (
    <div
      aria-hidden='true'
      className={cn(
        'pointer-events-none fixed inset-0 overflow-hidden',
        RARITY_TEXT_CLASS[rarity]
      )}
    >
      <div className='reveal-rays' data-strong={open || undefined} />
      <div className='reveal-glow' />
      {open && (
        <>
          <div className='reveal-burst' />
          <div className='reveal-sparks'>
            {Array.from({ length: SPARK_COUNT }, (_, index) => (
              <span key={index} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

type RevealSequenceProps = {
  item: RevealItem
  view: SonPublic | null
  remaining: number
  onNext: () => void
  onSkip: () => void
  onOpenPage: (() => void) | null
}

function RevealSequence({
  item,
  view,
  remaining,
  onNext,
  onSkip,
  onOpenPage,
}: RevealSequenceProps) {
  const state = useWorldState()
  const [open, setOpen] = useState(false)
  const rarity: Rarity = view?.son.rarity ?? item.rarity ?? 'common'
  const ready = view !== null
  useEffect(() => {
    if (!ready || open) return
    const timer = window.setTimeout(() => setOpen(true), CHARGE_MS[rarity])
    return () => window.clearTimeout(timer)
  }, [open, rarity, ready])
  const worldName = view
    ? (state.data?.worlds.find(
        (world) => world.id === view.son.current_world_id
      )?.name ?? null)
    : null
  return (
    <>
      <Effects rarity={rarity} open={open} />
      <div
        data-reveal-phase={open ? 'open' : 'sealed'}
        className='relative flex w-full max-w-md min-w-0 flex-col items-center gap-5 py-6'
      >
        <div className='flex min-w-0 flex-col items-center gap-1 text-center'>
          <Label variant='overline'>{KIND_LABEL[item.kind]}</Label>
          {open && view ? (
            <>
              <StageDialogTitle asChild>
                <PageTitle
                  className={cn(
                    'reveal-title flex items-center gap-2 uppercase',
                    RARITY_TEXT_CLASS[rarity]
                  )}
                >
                  <RarityIcon rarity={rarity} className='size-icon-xl' />
                  {RARITY_LABEL[rarity]}
                </PageTitle>
              </StageDialogTitle>
              {view.son.stars > 0 && (
                <span className='reveal-rise flex items-center gap-1'>
                  {Array.from({ length: view.son.stars }, (_, index) => (
                    <Star
                      key={index}
                      aria-hidden='true'
                      className={cn(
                        'size-icon-md fill-current',
                        RARITY_TEXT_CLASS[rarity]
                      )}
                    />
                  ))}
                </span>
              )}
            </>
          ) : (
            <StageDialogTitle asChild>
              <SectionTitle>{SEALED_TEXT[item.kind]}</SectionTitle>
            </StageDialogTitle>
          )}
          <StageDialogDescription className='sr-only'>
            {view
              ? `${view.son.name}, ${view.son.title}`
              : 'A son is being revealed'}
          </StageDialogDescription>
        </div>
        <div className='reveal-flip w-full min-w-0'>
          <div
            className={cn('reveal-flip-inner', !open && 'reveal-float')}
            data-flipped={open || undefined}
          >
            <CardBack
              rarity={rarity}
              kind={item.kind}
              charging={ready && !open}
              onReveal={() => ready && setOpen(true)}
            />
            <div className='reveal-face reveal-face-front min-w-0 text-left'>
              {view && (
                <SonCard
                  view={view}
                  ready={
                    state.data?.pending_son_ids.includes(view.son.id) ?? false
                  }
                  worldName={worldName}
                  interactive={false}
                />
              )}
            </div>
          </div>
        </div>
        {open && (
          <div className='reveal-rise-late flex w-full min-w-0 flex-wrap items-center justify-center gap-2'>
            {onOpenPage && (
              <Button variant='outline' onClick={onOpenPage}>
                <Crown />
                Open his page
              </Button>
            )}
            {remaining > 0 ? (
              <>
                <Button
                  onClick={onNext}
                  className='shadow-lg shadow-primary/30'
                >
                  <Sparkles />
                  {`Next son · ${remaining} left`}
                </Button>
                <Button variant='ghost' onClick={onSkip}>
                  <FastForward />
                  Skip the rest
                </Button>
              </>
            ) : (
              <Button onClick={onNext} className='shadow-lg shadow-primary/30'>
                Continue
              </Button>
            )}
          </div>
        )}
      </div>
    </>
  )
}

function rarityRank(view: SonPublic): number {
  return RARITIES.indexOf(view.son.rarity)
}

export function SonRevealOverlay() {
  const queryClient = useQueryClient()
  const { open } = useDrawerStack()
  const sons = useSons()
  const items = useRevealQueue((state) => state.items)
  const push = useRevealQueue((state) => state.push)
  const next = useRevealQueue((state) => state.next)
  const clear = useRevealQueue((state) => state.clear)
  const genesisPending = useRevealQueue((state) => state.genesisPending)
  const genesisDone = useRevealQueue((state) => state.genesisDone)
  useEffect(() => {
    if (!genesisPending || !sons.data || sons.data.length === 0) return
    push(
      [...sons.data]
        .sort((left, right) => rarityRank(left) - rarityRank(right))
        .map((view) => ({
          key: `genesis-${view.son.id}`,
          sonId: view.son.id,
          kind: 'genesis' as const,
          rarity: view.son.rarity,
        }))
    )
    genesisDone()
  }, [genesisDone, genesisPending, push, sons.data])
  useEvent('son.new', (event) => {
    void queryClient.invalidateQueries({ queryKey: godKeys.sons })
    const rarity = event.payload.rarity
    push([
      {
        key: `new-${event.payload.son_id}`,
        sonId: event.payload.son_id,
        kind: 'new',
        rarity: isRarity(rarity) ? rarity : null,
      },
    ])
  })
  useEvent('son.ascended', (event) => {
    void queryClient.invalidateQueries({ queryKey: godKeys.sons })
    const rarity = event.payload.rarity
    push([
      {
        key: `ascended-${event.payload.son_id}-${rarity}`,
        sonId: event.payload.son_id,
        kind: 'ascended',
        rarity: isRarity(rarity) ? rarity : null,
      },
    ])
  })
  useEvent('creator.revelation', (event) => {
    const entityId = event.payload.entity_id ?? event.payload.record_id
    const name = event.payload.name
    toast.success(name ? `${name} appeared` : 'Your revelation took shape', {
      action:
        typeof entityId === 'number'
          ? {
              label: 'Open',
              onClick: () => open({ kind: 'entity', id: String(entityId) }),
            }
          : undefined,
    })
  })
  const item = items[0] ?? null
  const view = item
    ? (item.preview ??
      sons.data?.find((entry) => entry.son.id === item.sonId) ??
      null)
    : null
  return (
    <StageDialog open={item !== null} onOpenChange={(next) => !next && clear()}>
      <StageDialogContent>
        <div className='fixed top-4 right-4'>
          <Button
            variant='ghost'
            size='icon'
            aria-label='Close the reveal'
            onClick={clear}
          >
            <X />
          </Button>
        </div>
        {item && (
          <RevealSequence
            key={item.key}
            item={item}
            view={view}
            remaining={items.length - 1}
            onNext={next}
            onSkip={clear}
            onOpenPage={
              item.preview
                ? null
                : () => {
                    clear()
                    open({ kind: 'son', id: String(item.sonId) })
                  }
            }
          />
        )}
      </StageDialogContent>
    </StageDialog>
  )
}
