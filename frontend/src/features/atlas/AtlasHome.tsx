import { Globe2, Library, Shapes, Star, UserRound } from 'lucide-react'
import { formatCompact } from '@/lib/format'
import { agree, plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MiniStat, Section } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { StarDisc, WorldDisc } from '@/features/cosmos/Glyphs'
import { useCosmos } from '@/features/entity/api/queries'

type AtlasHomeProps = {
  records: number
  kinds: number
  onSelect: (key: string) => void
}

export function AtlasHome({ records, kinds, onSelect }: AtlasHomeProps) {
  const cosmos = useCosmos()
  const worlds = cosmos.data?.worlds ?? []
  const stars = cosmos.data?.stars ?? []
  const palette = (type: string) =>
    cosmos.data?.world_types.find((item) => item.world_type === type)?.palette
      .biome_colours ?? []
  const souls = worlds.reduce((sum, item) => sum + item.counts.population, 0)
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <div className='grid min-w-0 grid-cols-2 gap-2 @lg/pane:grid-cols-4'>
        <MiniStat
          icon={Library}
          tone='verdigris'
          label='Records'
          value={formatCompact(records)}
        />
        <MiniStat icon={Shapes} tone='gold' label='Kinds' value={kinds} />
        <MiniStat
          icon={Star}
          tone='warning'
          label='Stars'
          value={stars.length}
        />
        <MiniStat
          icon={Globe2}
          tone='info'
          label='Worlds'
          value={worlds.length}
        />
      </div>
      <Section
        title='Worlds'
        description={`${formatCompact(souls)} ${agree(souls, 'soul', 'souls')} live across the cosmos. Open a world to read its lore, peoples and chronicle.`}
      >
        <ul className='grid min-w-0 grid-cols-1 gap-2 @sm/pane:grid-cols-2'>
          {worlds.map((item) => (
            <li
              key={item.world.id}
              className='flex min-w-0 items-center gap-3 rounded-xl border bg-background p-3'
            >
              <WorldDisc
                palette={palette(item.world.world_type)}
                cover={item.cover}
              />
              <span className='flex min-w-0 flex-1 flex-col items-start gap-1'>
                <Button
                  variant='link'
                  size='sm'
                  onClick={() => onSelect(`world:${item.world.id}`)}
                >
                  {item.world.name}
                </Button>
                <span className='flex min-w-0 flex-wrap items-center gap-1.5'>
                  <Badge size='sm' variant='outline'>
                    {item.type_label}
                  </Badge>
                  <Badge size='sm' variant='info'>
                    <UserRound />
                    {formatCompact(item.counts.population)}
                  </Badge>
                </span>
              </span>
            </li>
          ))}
        </ul>
      </Section>
      {stars.length > 0 && (
        <Section title='Stars'>
          <ul className='grid min-w-0 grid-cols-1 gap-2 @sm/pane:grid-cols-2'>
            {stars.map((star) => {
              const circling = worlds.filter(
                (item) => item.world.star_id === star.id
              ).length
              return (
                <li
                  key={star.id}
                  className='flex min-w-0 items-center gap-3 rounded-xl border bg-background p-3'
                >
                  <StarDisc type={star.star_type} cover={star.cover} />
                  <span className='flex min-w-0 flex-1 flex-col items-start gap-1'>
                    <Button
                      variant='link'
                      size='sm'
                      onClick={() => onSelect(`star:${star.id}`)}
                    >
                      {star.name}
                    </Button>
                    <Muted variant='caption' truncate>
                      {circling > 0
                        ? `${plural(circling, 'world', 'worlds')} in its light`
                        : 'Burns alone'}
                    </Muted>
                  </span>
                </li>
              )
            })}
          </ul>
        </Section>
      )}
      <Label>
        Pick anything in the tree or the list to read its page here.
      </Label>
    </div>
  )
}
