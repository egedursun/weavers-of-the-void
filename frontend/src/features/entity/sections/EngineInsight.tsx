import {
  BookOpen,
  Church,
  Cog,
  Crown,
  Gem,
  Hourglass,
  PackageX,
  Repeat,
  Sparkles,
  Undo2,
} from 'lucide-react'
import { knowledgeBranchValues } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { EntityLink, MiniStat, PagedList } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { type EntityContext } from '../actions/context'
import { humanize } from '../actions/schema'

export function EngineInsight({ ctx }: { ctx: EntityContext }) {
  const { knowledge, resource, faith, reward } = ctx.detail.insight
  if (!knowledge && !resource && !faith && !reward) return null
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
                ? `${wordOf(knowledgeBranchValues, knowledge.branch)} multiplier`
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
          <div className='flex min-w-0 flex-col gap-2'>
            <PagedList
              items={resource.mechanics}
              initial={12}
              noun={['entry', 'entries']}
              as='div'
              className='flex min-w-0 flex-wrap items-center gap-1.5'
              itemKey={(mechanic) => mechanic}
            >
              {(mechanic) => (
                <Badge key={mechanic} size='sm' variant='info'>
                  <Cog />
                  {humanize(mechanic)}
                </Badge>
              )}
            </PagedList>
            <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
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
      {reward && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Creation reward</Label>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            {reward.son && (
              <Badge size='sm' variant='outline'>
                <Sparkles />
                <EntityLink kind='son' id={String(reward.son.id)}>
                  {reward.son.name}
                </EntityLink>
              </Badge>
            )}
            {reward.partner && (
              <Badge size='sm' variant='outline'>
                <Sparkles />
                <EntityLink kind='son' id={String(reward.partner.id)}>
                  {reward.partner.name}
                </EntityLink>
                {` · ${formatInteger(reward.partner_xp)} XP · ${formatInteger(reward.partner_renown)} renown`}
              </Badge>
            )}
            {reward.land && (
              <Badge size='sm' variant='info'>
                Land
              </Badge>
            )}
            {reward.has_thread && (
              <Badge
                size='sm'
                variant={reward.thread_reverted ? 'warning' : 'outline'}
              >
                <Undo2 />
                {reward.thread_reverted
                  ? 'Storyline reverted'
                  : 'Moved a storyline'}
              </Badge>
            )}
          </div>
          <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
            <MiniStat
              icon={Crown}
              tone='gold'
              label='XP'
              value={formatInteger(reward.xp)}
            />
            <MiniStat
              icon={Sparkles}
              tone='info'
              label='Renown'
              value={formatInteger(reward.renown)}
            />
            <MiniStat
              icon={Gem}
              tone='verdigris'
              label='Essence'
              value={formatInteger(reward.essence)}
              hint={`Cost ${formatInteger(reward.cost)} essence`}
            />
            <MiniStat
              icon={Hourglass}
              tone='muted'
              label='Reward kept'
              value={`${reward.fade_pct}%`}
              hint='Repeated creations of the same kind earn less'
            />
            <MiniStat
              icon={Repeat}
              tone='muted'
              label='Repeats'
              value={formatInteger(reward.repeats)}
            />
            <MiniStat
              icon={Undo2}
              tone={reward.taken_back_pct > 0 ? 'warning' : 'success'}
              label='Taken back'
              value={`${reward.taken_back_pct}%`}
              hint={reward.reason ?? undefined}
            />
          </div>
        </div>
      )}
    </div>
  )
}
