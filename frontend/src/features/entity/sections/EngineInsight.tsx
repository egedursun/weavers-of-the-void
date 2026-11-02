import { BookOpen, Church, Cog, PackageX } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { EntityLink, MiniStat } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { type EntityContext } from '../actions/context'
import { humanize } from '../actions/schema'

export function EngineInsight({ ctx }: { ctx: EntityContext }) {
  const { knowledge, resource, faith } = ctx.detail.insight
  if (!knowledge && !resource && !faith) return null
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {knowledge && (
        <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
          <MiniStat
            icon={BookOpen}
            tone='info'
            label='Knowledge level'
            value={`${knowledge.level} / ${knowledge.level_cap}`}
          />
          <MiniStat
            icon={Cog}
            tone='verdigris'
            label={
              knowledge.branch
                ? `${humanize(knowledge.branch)} multiplier`
                : 'Branch multiplier'
            }
            value={`×${knowledge.branch_multiplier}`}
            hint='How much this knowledge strengthens its branch in war, trade, food and craft'
          />
        </div>
      )}
      {resource && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Mechanics</Label>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            {resource.mechanics.map((mechanic) => (
              <Badge key={mechanic} size='sm' variant='info'>
                <Cog />
                {humanize(mechanic)}
              </Badge>
            ))}
            {resource.mechanics.length === 0 && (
              <Muted variant='caption'>
                {resource.weighed
                  ? 'Weighed: it works no special rule.'
                  : 'Not weighed yet; it is given a working at the next epoch end.'}
              </Muted>
            )}
            {resource.depleting && (
              <Badge size='sm' variant='warning'>
                <PackageX />
                Depleting
              </Badge>
            )}
            {resource.depleted && (
              <Badge size='sm' variant='destructive'>
                <PackageX />
                Depleted
              </Badge>
            )}
          </div>
        </div>
      )}
      {faith && (faith.revered.length > 0 || faith.syncretic) && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Old gods</Label>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            {faith.syncretic && (
              <Badge size='sm' variant='warning'>
                <Church />
                Syncretic faith
              </Badge>
            )}
            {faith.revered.map((god) => (
              <Badge key={god.id} size='sm' variant='outline'>
                <EntityLink kind='foreign-god' id={String(god.id)}>
                  {god.name}
                </EntityLink>
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
