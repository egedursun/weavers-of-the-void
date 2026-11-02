import { useMemo, useState } from 'react'
import { Sparkles, Star, StarOff } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, EntityLink, MiniStat, Section } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { ENTITY_TYPE_ICON } from '@/components/domain/domainIcons'
import { Muted, Text } from '@/components/typography'
import { humanize } from '@/features/entity/actions/schema'
import { useLoreMutation } from '@/features/entity/api/mutations'
import { useNames } from '@/features/entity/api/queries'
import { mediaUrl } from '@/features/images/media'
import { type FavoriteCard, setFavorite, useFavoriteBoard } from './api'

const COVER_WIDTH = 320

function useToggleFavorite() {
  return useLoreMutation({
    run: ({ id, next }: { id: number; next: boolean }) => setFavorite(id, next),
    success: (_result, { next }) =>
      next ? 'Added to favourites' : 'Removed from favourites',
  })
}

function Card({
  card,
  pinned,
  busy,
  onToggle,
}: {
  card: FavoriteCard
  pinned: boolean
  busy: boolean
  onToggle: () => void
}) {
  const entity = card.entity
  const Icon = ENTITY_TYPE_ICON[entity.entity_type]
  return (
    <li
      className={cn(
        'group relative flex min-w-0 flex-col overflow-hidden rounded-xl border bg-background',
        pinned && 'border-primary/40'
      )}
    >
      <div className='relative aspect-square w-full overflow-hidden bg-muted'>
        {card.cover ? (
          <img
            src={mediaUrl(card.cover, COVER_WIDTH) ?? undefined}
            alt={entity.name}
            loading='lazy'
            decoding='async'
            className='size-full object-cover transition-transform duration-300 group-hover:scale-105'
          />
        ) : (
          <span className='flex size-full items-center justify-center text-muted-foreground'>
            <Icon aria-hidden='true' className='size-icon-xl' />
          </span>
        )}
        <span className='absolute top-2 left-2'>
          <Badge size='sm' variant='secondary'>
            <Icon />
            {humanize(entity.entity_type)}
          </Badge>
        </span>
        <span className='absolute top-2 right-2'>
          <Button
            size='icon-sm'
            variant={pinned ? 'default' : 'secondary'}
            aria-label={
              pinned
                ? `Remove ${entity.name} from favourites`
                : `Add ${entity.name} to favourites`
            }
            aria-pressed={pinned}
            disabled={busy}
            disabledReason='Saving'
            onClick={onToggle}
          >
            {pinned ? <Star className='fill-current' /> : <Star />}
          </Button>
        </span>
      </div>
      <div className='flex min-w-0 flex-col gap-0.5 p-2.5'>
        <EntityLink kind='entity' id={String(entity.id)}>
          {entity.name}
        </EntityLink>
        <Muted as='span' variant='caption' truncate>
          {entity.subtype
            ? `${entity.subtype} · epoch ${entity.birth_epoch}`
            : `Epoch ${entity.birth_epoch}`}
        </Muted>
      </div>
    </li>
  )
}

function CardGrid({
  cards,
  pinned,
  toggle,
}: {
  cards: FavoriteCard[]
  pinned: boolean
  toggle: ReturnType<typeof useToggleFavorite>
}) {
  return (
    <ul className='grid min-w-0 grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6'>
      {cards.map((card) => (
        <Card
          key={card.entity.id}
          card={card}
          pinned={pinned}
          busy={toggle.isPending && toggle.variables?.id === card.entity.id}
          onToggle={() => toggle.mutate({ id: card.entity.id, next: !pinned })}
        />
      ))}
    </ul>
  )
}

export function Bookmarks() {
  const board = useFavoriteBoard()
  const names = useNames()
  const toggle = useToggleFavorite()
  const [picked, setPicked] = useState<string | null>(null)
  const favorites = useMemo(() => board.data?.favorites ?? [], [board.data])
  const suggestions = board.data?.suggestions ?? []
  const pinnedIds = useMemo(
    () => new Set(favorites.map((card) => card.entity.id)),
    [favorites]
  )
  const options = useMemo(
    () =>
      (names.data ?? [])
        .filter((entry) => entry.kind === 'entity' && !pinnedIds.has(entry.id))
        .map((entry) => ({
          value: String(entry.id),
          label: entry.name,
          hint: humanize(entry.type),
        })),
    [names.data, pinnedIds]
  )
  const kinds = new Set(favorites.map((card) => card.entity.entity_type)).size
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
        <MiniStat
          icon={Star}
          label='Favourites'
          value={favorites.length}
          tone='gold'
        />
        <MiniStat
          icon={Sparkles}
          label='Kinds kept close'
          value={kinds}
          tone='verdigris'
        />
        <MiniStat
          icon={StarOff}
          label='Worth a look'
          value={suggestions.length}
          tone='info'
          hint='The most important records you have not starred yet'
        />
      </div>
      <Section
        id='bookmarks-favorites'
        title={`Favourite records · ${formatInteger(favorites.length)}`}
        description='Records you starred. They lead the search palette and stay one click away.'
        level={3}
        actions={
          <div className='w-full min-w-0 sm:w-72'>
            <RecordCombobox
              options={options}
              value={picked}
              placeholder='Star any record'
              searchPlaceholder='Search records'
              emptyText='No record by that name'
              size='sm'
              disabled={toggle.isPending}
              disabledReason='Saving'
              onChange={(value) => {
                setPicked(null)
                if (value) toggle.mutate({ id: Number(value), next: true })
              }}
            />
          </div>
        }
      >
        {board.isPending && <Skeleton className='h-textarea w-full' />}
        {board.isError && <Text tone='destructive'>{board.error.message}</Text>}
        {board.data && favorites.length === 0 && (
          <EmptyState
            size='compact'
            icon={Star}
            title='No favourites yet'
            description='Star a record here, on its page, or from the suggestions below.'
          />
        )}
        {favorites.length > 0 && (
          <CardGrid cards={favorites} pinned toggle={toggle} />
        )}
      </Section>
      {suggestions.length > 0 && (
        <Section
          id='bookmarks-suggestions'
          title='Worth keeping close'
          description='The most important records of the world. Star the ones you want at hand.'
          level={3}
        >
          <CardGrid cards={suggestions} pinned={false} toggle={toggle} />
        </Section>
      )}
    </div>
  )
}
