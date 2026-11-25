import { ChevronRight, Printer, Star, StarOff } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  domainValues,
  entityOriginValues,
  entityStatusValues,
  entityTypeValues,
  legendCategoryValues,
} from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EntityLink, HeroFrame, Paged } from '@/components/domain'
import { DomainIcon } from '@/components/domain/DomainIcon'
import { RecordNavLink } from '@/components/domain/RecordNavLink'
import { Label, Muted, PageTitle } from '@/components/typography'
import { bookUrl } from '@/features/chronicle/api'
import { ArmsCrest } from '@/features/collective/ArmsCrest'
import { wordOf } from '@/features/entity/affairs/labels'
import { PortraitGenerateOverlay } from '@/features/images/PortraitGenerateOverlay'
import { useLoreMutation } from '../api/mutations'
import { useCatalogue, useWorldState } from '../api/queries'
import { type EntityDetail } from '../api/types'
import { EntityLevel } from './EntityLevel'
import { TagChips } from './TagChips'

type EntityHeroProps = {
  detail: EntityDetail
  onOpenImages: () => void
  readOnlyReason: string | null
}

const STATUS_TONE: Record<
  string,
  'destructive' | 'secondary' | 'warning' | 'success'
> = {
  canon: 'success',
  rejected: 'warning',
  destroyed: 'destructive',
  dead: 'secondary',
  fulfilled: 'success',
}

export function EntityHero({
  detail,
  onOpenImages,
  readOnlyReason,
}: EntityHeroProps) {
  const entity = detail.entity
  const catalogue = useCatalogue()
  const state = useWorldState()
  const typeLabel =
    catalogue.data?.entity_types.find((item) => item.key === entity.entity_type)
      ?.label ?? wordOf(entityTypeValues, entity.entity_type)
  const domainLabel = entity.domain
    ? (catalogue.data?.domains.find((item) => item.key === entity.domain)
        ?.label ?? wordOf(domainValues, entity.domain))
    : null
  const worlds = state.data?.worlds ?? []
  const world = worlds.find((item) => item.id === entity.world_id)
  const multiWorld = worlds.length > 1
  const dead = entity.status === 'dead' || entity.status === 'destroyed'
  const favorite = useLoreMutation({
    writes: [{ lever: 'record:favorite' }],
    run: (next: boolean) =>
      unwrap(
        api.PUT('/api/entities/{entity_id}/favorite', {
          params: { path: { entity_id: entity.id } },
          body: { favorite: next },
        })
      ),
    success: (_result, next) =>
      next ? 'Added to favourites' : 'Removed from favourites',
  })
  const shownFavorite = favorite.isPending
    ? (favorite.variables ?? entity.favorite)
    : entity.favorite
  return (
    <HeroFrame>
      <header
        data-entity-hero={entity.id}
        data-entry-kind={typeLabel}
        className='flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start'
      >
        <PortraitGenerateOverlay
          nodeId={entity.id}
          name={entity.name}
          cover={detail.cover}
          veiled={entity.entity_type === 'outer_being'}
          onOpen={onOpenImages}
          readOnlyReason={readOnlyReason}
        />
        <ArmsCrest nodeId={entity.id} name={entity.name} />
        <div className='flex min-w-0 flex-1 flex-col gap-2'>
          <nav
            aria-label='Location'
            className='flex min-w-0 flex-wrap items-center gap-1'
          >
            {detail.breadcrumb.length === 0 ? (
              <Label>Top level</Label>
            ) : (
              detail.breadcrumb.map((ref, index) => (
                <span key={ref.id} className='flex min-w-0 items-center gap-1'>
                  {index > 0 && (
                    <ChevronRight
                      aria-hidden='true'
                      className='size-icon-xs text-muted-foreground'
                    />
                  )}
                  <EntityLink kind='entity' id={String(ref.id)}>
                    {ref.name}
                  </EntityLink>
                </span>
              ))
            )}
          </nav>
          {detail.level && entity.location_id !== null ? (
            <EntityLevel
              entityId={entity.id}
              locationId={entity.location_id}
              level={detail.level}
              readOnlyReason={readOnlyReason}
            />
          ) : null}
          <PageTitle truncate={2}>
            {dead ? `† ${entity.name}` : entity.name}
          </PageTitle>
          <Muted>{entity.title ?? entity.subtype ?? typeLabel}</Muted>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Button
              act={favorite}
              variant={shownFavorite ? 'secondary' : 'outline'}
              size='sm'
              aria-pressed={shownFavorite}
              disabled={readOnlyReason !== null}
              disabledReason={readOnlyReason ?? undefined}
              onClick={() => favorite.mutate(!shownFavorite)}
            >
              {shownFavorite ? (
                <Star className='fill-current text-primary' />
              ) : (
                <StarOff />
              )}
              {shownFavorite ? 'Favourite' : 'Add to favourites'}
            </Button>
            <RecordNavLink
              to={{ view: 'map', world: entity.world_id, focus: entity.id }}
            />
            <RecordNavLink to={{ view: 'network', focus: entity.id }} />
            <RecordNavLink
              to={{
                view: 'chronicle',
                epoch: entity.birth_epoch,
                world: multiWorld ? entity.world_id : null,
              }}
            />
            <RecordNavLink to={{ view: 'atlas', type: entity.entity_type }}>
              {`${typeLabel} in the atlas`}
            </RecordNavLink>
            {world && (
              <RecordNavLink to={{ view: 'climate', world: world.id }}>
                {`Climate of ${world.name}`}
              </RecordNavLink>
            )}
            <Button variant='outline' size='sm' asChild>
              <a
                href={bookUrl({ entity_id: entity.id })}
                target='_blank'
                rel='noreferrer'
              >
                <Printer />
                Print page
              </a>
            </Button>
          </div>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Badge variant='outline'>
              <DomainIcon vocabulary='entity-type' value={entity.entity_type} />
              {typeLabel}
            </Badge>
            <Badge variant='outline'>{`Power ${formatInteger(entity.power_level)}`}</Badge>
            {domainLabel && <Badge variant='outline'>{domainLabel}</Badge>}
            {entity.legend_category && (
              <Badge variant='outline'>{`A legend of a ${wordOf(legendCategoryValues, entity.legend_category).toLowerCase()}`}</Badge>
            )}
            {entity.map_x !== null && entity.map_y !== null && (
              <Badge variant='outline'>{`On the map at ${formatInteger(entity.map_x)}, ${formatInteger(entity.map_y)}`}</Badge>
            )}
            <Badge variant='outline'>{`Epoch ${formatInteger(entity.birth_epoch)}`}</Badge>
            {entity.status !== 'canon' && (
              <Badge variant={STATUS_TONE[entity.status] ?? 'secondary'}>
                {wordOf(entityStatusValues, entity.status)}
              </Badge>
            )}
            {detail.creator_son ? (
              <Badge variant='outline' asChild>
                <EntityLink kind='son' id={String(detail.creator_son.id)}>
                  {`by ${detail.creator_son.name}`}
                </EntityLink>
              </Badge>
            ) : detail.maker ? (
              <Badge variant='outline' asChild>
                <EntityLink kind='entity' id={String(detail.maker.id)}>
                  {`made by ${detail.maker.name}`}
                </EntityLink>
              </Badge>
            ) : (
              <Badge variant='outline'>
                {entity.origin === 'engine'
                  ? "the world's flow"
                  : wordOf(entityOriginValues, entity.origin)}
              </Badge>
            )}
            {multiWorld && world && (
              <Badge variant='outline' asChild>
                <EntityLink kind='world-guide' id={String(world.id)} showIcon>
                  {world.name}
                </EntityLink>
              </Badge>
            )}
            {detail.importance?.archived && (
              <Badge
                variant='secondary'
                title={`Importance ${detail.importance.importance} · last mentioned in epoch ${detail.importance.last_mention}`}
              >
                {detail.importance.reason
                  ? `Sank into history: ${detail.importance.reason}`
                  : 'Sank into history'}
              </Badge>
            )}
            {detail.patron && (
              <Badge variant='outline'>{`Worships ${detail.patron.name}`}</Badge>
            )}
            <Paged items={detail.anchored_sons}>
              {(son) => (
                <Badge key={son.id} variant='outline' asChild>
                  <EntityLink kind='son' id={String(son.id)}>
                    {`${son.name}'s anchor`}
                  </EntityLink>
                </Badge>
              )}
            </Paged>
            <TagChips detail={detail} />
          </div>
        </div>
      </header>
    </HeroFrame>
  )
}
