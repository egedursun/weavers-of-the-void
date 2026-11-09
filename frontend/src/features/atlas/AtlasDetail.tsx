import { BookOpen, ExternalLink } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState, Portrait, RarityBadge } from '@/components/domain'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { Label, Muted, PageTitle } from '@/components/typography'
import { StarWikiView } from '@/features/celestial/StarWikiPage'
import { WorldWikiView } from '@/features/celestial/WorldWikiPage'
import { ClusterView } from '@/features/cosmography/wiki/ClusterWiki'
import { DimensionView } from '@/features/cosmography/wiki/DimensionWiki'
import { GalaxyView } from '@/features/cosmography/wiki/GalaxyWiki'
import { EntityView } from '@/features/entity/EntityView'
import { humanize } from '@/features/entity/actions/schema'
import { useCosmos, useWorldState } from '@/features/entity/api/queries'
import { mediaUrl } from '@/features/pantheon/media'
import { AtlasGroup } from './AtlasGroup'
import { AtlasHome } from './AtlasHome'
import { type AtlasNode } from './atlasModel'
import { parseSelection } from './atlasSearch'

type AtlasDetailProps = {
  selection: string | null
  group?: AtlasNode | null
  records: number
  kinds: number
  onSelect: (key: string) => void
}

function OpenInDrawer({ kind, id }: { kind: DrawerKind; id: number | null }) {
  const drawers = useDrawerStack()
  return (
    <Button
      variant='outline'
      size='sm'
      className='self-end'
      onClick={() =>
        drawers.open({
          kind,
          id: kind === 'creator' || id === null ? undefined : String(id),
        })
      }
    >
      <ExternalLink />
      Open as a page
    </Button>
  )
}

export function AtlasDetail({
  selection,
  group = null,
  records,
  kinds,
  onSelect,
}: AtlasDetailProps) {
  const state = useWorldState()
  const cosmos = useCosmos()
  const parsed = parseSelection(selection)
  if (group) return <AtlasGroup node={group} onSelect={onSelect} />
  if (!parsed)
    return <AtlasHome records={records} kinds={kinds} onSelect={onSelect} />
  if (parsed.kind === 'entity') return <EntityView id={parsed.id} />
  if (parsed.kind === 'world' && parsed.id !== null)
    return (
      <div className='flex min-w-0 flex-col gap-3'>
        <OpenInDrawer kind='world' id={parsed.id} />
        <WorldWikiView worldId={parsed.id} />
      </div>
    )
  if (parsed.kind === 'galaxy' && parsed.id !== null)
    return (
      <div className='flex min-w-0 flex-col gap-3'>
        <OpenInDrawer kind='galaxy' id={parsed.id} />
        <GalaxyView galaxyId={parsed.id} />
      </div>
    )
  if (parsed.kind === 'cluster' && parsed.id !== null)
    return (
      <div className='flex min-w-0 flex-col gap-3'>
        <OpenInDrawer kind='cluster' id={parsed.id} />
        <ClusterView clusterId={parsed.id} />
      </div>
    )
  if (parsed.kind === 'dimension' && parsed.id !== null)
    return (
      <div className='flex min-w-0 flex-col gap-3'>
        <OpenInDrawer kind='dimension' id={parsed.id} />
        <DimensionView dimensionId={parsed.id} />
      </div>
    )
  if (parsed.kind === 'star' && parsed.id !== null)
    return (
      <div className='flex min-w-0 flex-col gap-3'>
        <OpenInDrawer kind='star' id={parsed.id} />
        <StarWikiView starId={parsed.id} />
      </div>
    )
  const sonView =
    parsed.kind === 'son'
      ? state.data?.sons.find((view) => view.son.id === parsed.id)
      : undefined
  const god =
    parsed.kind === 'foreign-god'
      ? cosmos.data?.foreign_gods.find((item) => item.id === parsed.id)
      : undefined
  const creator = parsed.kind === 'creator' ? state.data?.creator : undefined
  const name = sonView?.son.name ?? god?.name ?? creator?.name
  if (!name)
    return (
      <EmptyState
        icon={BookOpen}
        title='Nothing here'
        description='This record is no longer part of the world.'
      />
    )
  const cover = sonView
    ? sonView.cover
    : god
      ? god.cover
      : state.data?.creator_cover
  const subtitle =
    sonView?.son.title ?? god?.title ?? creator?.title ?? undefined
  const story =
    sonView?.son.plan ?? god?.description ?? creator?.appearance ?? undefined
  const drawer: DrawerKind = sonView ? 'son' : god ? 'foreign-god' : 'creator'
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <OpenInDrawer kind={drawer} id={parsed.id} />
      <div className='flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start'>
        <Portrait
          name={name}
          src={mediaUrl(cover)}
          size='xl'
          shape='square'
          rarity={sonView?.son.rarity ?? (god ? 'mythic' : 'legendary')}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-2'>
          <Label variant='overline'>{humanize(parsed.kind)}</Label>
          <PageTitle truncate={2}>{name}</PageTitle>
          {subtitle && <Muted>{subtitle}</Muted>}
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            {sonView && <RarityBadge rarity={sonView.son.rarity} size='sm' />}
            {sonView && (
              <Badge size='sm' variant='outline'>
                {humanize(sonView.son.status)}
              </Badge>
            )}
            {god && (
              <Badge size='sm' variant='outline'>
                {humanize(god.status)}
              </Badge>
            )}
          </div>
          {story && <Muted variant='caption'>{story}</Muted>}
        </div>
      </div>
    </div>
  )
}
