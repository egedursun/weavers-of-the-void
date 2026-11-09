import {
  CalendarDays,
  Globe2,
  Sparkles,
  Star,
  Sun,
  UserRound,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatCompact } from '@/lib/format'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  EntityLink,
  MiniStat,
  PagedList,
  Portrait,
  Section,
} from '@/components/domain'
import { type DrawerPageProps } from '@/components/layout/drawer/DrawerStack'
import { Label, Muted, PageTitle, Stat, Text } from '@/components/typography'
import { StarLifeSection } from '@/features/cosmography/HeavenlyLife'
import { StarDisc } from '@/features/cosmos/Glyphs'
import {
  DEAD_STAR_TYPES,
  SKY_EVENT_LABEL,
} from '@/features/cosmos/model/labels'
import { ThingSections } from '@/features/entity/sections/ThingSections'
import { PortraitGenerateOverlay } from '@/features/images/PortraitGenerateOverlay'
import { RecordGallery } from '@/features/pantheon/RecordGallery'
import { mediaUrl } from '@/features/pantheon/media'
import { CelestialDepthSection } from './CelestialDepthSection'
import { CelestialTimeline } from './WorldWikiPage'
import { type StarWiki, useStarWiki } from './api'

const PERCENT = 100

function StarHero({ wiki }: { wiki: StarWiki }) {
  const star = wiki.star
  const dead = DEAD_STAR_TYPES.has(star.star_type)
  return (
    <header className='flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start'>
      <PortraitGenerateOverlay
        nodeId={star.id}
        name={star.name}
        cover={wiki.cover ?? null}
        placeholder={
          <div className='flex size-portrait-xl shrink-0 items-center justify-center rounded-xl border bg-card'>
            <StarDisc type={star.star_type} />
          </div>
        }
      />
      <div className='flex min-w-0 flex-1 flex-col gap-2'>
        <Label variant='overline'>{`Star · ${wiki.type_label}`}</Label>
        <PageTitle truncate={2}>{star.name}</PageTitle>
        {star.description && <Muted>{star.description}</Muted>}
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Badge size='sm' variant={dead ? 'destructive' : 'default'}>
            <Sun />
            {dead ? 'Its light is gone' : 'Burning'}
          </Badge>
          <Badge size='sm' variant='outline'>
            <CalendarDays />
            {`Kindled in epoch ${star.created_epoch}`}
          </Badge>
        </div>
        <div className='flex max-w-sm min-w-0 flex-col gap-1.5'>
          <div className='flex min-w-0 items-center justify-between gap-2'>
            <Label>Brightness</Label>
            <Stat value={star.brightness} unit={`/ ${PERCENT}`} />
          </div>
          <Progress size='sm' value={star.brightness} aria-label='Brightness' />
        </div>
      </div>
    </header>
  )
}

function OrbitingWorlds({ wiki }: { wiki: StarWiki }) {
  const souls = wiki.worlds.reduce((sum, item) => sum + item.population, 0)
  return (
    <Section
      title='Worlds in its light'
      description={
        wiki.worlds.length > 0
          ? `${wiki.worlds.length} worlds circle it, home to ${formatCompact(souls)} souls.`
          : undefined
      }
    >
      {wiki.worlds.length === 0 ? (
        <EmptyState
          icon={Globe2}
          size='compact'
          title='No world circles this star'
          description='It burns alone in the void.'
        />
      ) : (
        <PagedList
          items={wiki.worlds}
          initial={8}
          noun={['world', 'worlds']}
          className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
          itemKey={(item) => item.world.id}
        >
          {(item) => (
            <li className='flex min-w-0 items-center gap-3 rounded-xl border bg-background p-3'>
              <Portrait
                name={item.world.name}
                src={mediaUrl(item.cover)}
                size='md'
              />
              <span className='flex min-w-0 flex-1 flex-col gap-1'>
                <EntityLink kind='world' id={String(item.world.id)}>
                  {item.world.name}
                </EntityLink>
                <span className='flex min-w-0 flex-wrap items-center gap-1.5'>
                  <Badge size='sm' variant='outline'>
                    {item.type_label}
                  </Badge>
                  <Badge size='sm' variant='info'>
                    <UserRound />
                    {formatCompact(item.population)}
                  </Badge>
                </span>
              </span>
            </li>
          )}
        </PagedList>
      )}
    </Section>
  )
}

export function StarWikiView({ starId }: { starId: number }) {
  const wiki = useStarWiki(starId)
  if (wiki.isPending)
    return (
      <div className='flex flex-col gap-4'>
        <Skeleton className='h-control-lg w-2/3' />
        <Skeleton className='h-textarea w-full' />
      </div>
    )
  if (wiki.isError)
    return (
      <Alert variant='destructive'>
        <Star />
        <AlertTitle>This star could not be read</AlertTitle>
        <AlertDescription>{wiki.error.message}</AlertDescription>
      </Alert>
    )
  const data = wiki.data
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <StarHero wiki={data} />
      <Section title='At a glance'>
        <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
          <MiniStat
            icon={Sun}
            tone='gold'
            label='Kind'
            value={data.type_label}
          />
          <MiniStat
            icon={Globe2}
            tone='info'
            label='Worlds'
            value={data.worlds.length}
          />
          <MiniStat
            icon={Sparkles}
            tone='verdigris'
            label='Sky events'
            value={data.sky_events.length}
          />
        </div>
      </Section>
      <StarLifeSection star={data.star} />
      <CelestialDepthSection
        kind='star'
        id={data.star.id}
        name={data.star.name}
        depth={data.depth ?? null}
      />
      <OrbitingWorlds wiki={data} />
      {data.sky_events.length > 0 && (
        <Section title='Signs in the sky'>
          <PagedList
            items={data.sky_events}
            initial={5}
            noun={['sky event', 'sky events']}
            className='flex min-w-0 flex-col gap-1.5'
            itemKey={(event) => event.id}
          >
            {(event) => (
              <li className='flex min-w-0 items-start gap-2 rounded-lg border bg-muted/30 p-2'>
                <Sparkles
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-primary'
                />
                <span className='flex min-w-0 flex-1 flex-col'>
                  <Text as='span' weight='medium'>
                    {SKY_EVENT_LABEL[event.kind]}
                  </Text>
                  {event.text && <Muted variant='caption'>{event.text}</Muted>}
                </span>
                <Badge
                  size='sm'
                  variant='outline'
                >{`Epoch ${event.epoch}`}</Badge>
              </li>
            )}
          </PagedList>
        </Section>
      )}
      <CelestialTimeline
        lines={data.timeline}
        emptyText='The chronicle has not named this star yet.'
      />
      <RecordGallery
        title='Images of the star'
        nodeId={data.star.id}
        name={data.star.name}
        images={data.images}
        prompt={data.star.image_prompt ?? null}
        promptLabel='Image prompt'
        onSavePrompt={(prompt) =>
          unwrap(
            api.PATCH('/api/stars/{star_id}', {
              params: { path: { star_id: data.star.id } },
              body: { image_prompt: prompt },
            })
          )
        }
      />
      <ThingSections nodeId={data.star.id} />
    </div>
  )
}

export function StarWikiPage({ id }: DrawerPageProps) {
  const starId = Number(id)
  if (!Number.isInteger(starId) || starId <= 0)
    return (
      <EmptyState
        icon={Star}
        title='No such star'
        description='This link does not point to a star.'
      />
    )
  return <StarWikiView starId={starId} />
}
