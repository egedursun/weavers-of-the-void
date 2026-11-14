import { BookOpen, Flame, MoonStar, Trash2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatDecimal } from '@/lib/format'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { PagedList, Section } from '@/components/domain'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { Label, Muted, SectionTitle, Text } from '@/components/typography'
import { CosmicActionButton } from './CosmicActionButton'
import { StarDisc } from './Glyphs'
import { StarEditForm } from './StarEditForm'
import { type StarRecord } from './api'
import { type CosmosIndex } from './model/cosmosModel'
import { DEAD_STAR_TYPES, STAR_TYPE_LABEL } from './model/labels'
import { type RuleBook, ruleText } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

type StarCardProps = {
  star: StarRecord
  index: CosmosIndex
  rules: RuleBook
  onSelectWorld: (worldId: number) => void
}

export function StarCard({ star, index, rules, onSelectWorld }: StarCardProps) {
  const drawers = useDrawerStack()
  const planets = index.planetsOf(star.id)
  const orbiting = index.worlds.filter((item) => item.world.star_id === star.id)
  const rekindle = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/cosmic/rekindle-star', { body: { star_id: star.id } })
      ),
    success: 'The dead star burns again',
  })
  const extinguish = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cosmic:extinguish_star', {
          body: { star_id: star.id },
        })
      ),
  })
  const remove = useCosmicAction({
    run: () =>
      unwrap(
        api.DELETE('/api/stars/{star_id}', {
          params: { path: { star_id: star.id } },
        })
      ),
    success: `${star.name} was removed from the sky`,
  })
  return (
    <article data-star-id={star.id} className='flex min-w-0 flex-col gap-6'>
      <header className='flex min-w-0 items-center gap-3'>
        <StarDisc type={star.star_type} cover={star.cover} />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Label variant='overline' truncate>
            {`${STAR_TYPE_LABEL[star.star_type]} · brightness ${star.brightness}`}
          </Label>
          <SectionTitle level={3} truncate={2}>
            {star.name}
          </SectionTitle>
          <Muted variant='caption'>
            {`${plural(planets.length, 'planet', 'planets')} · position ${formatDecimal(star.x)}, ${formatDecimal(star.y)}`}
          </Muted>
        </div>
      </header>
      {star.description && <Text variant='prose'>{star.description}</Text>}
      {DEAD_STAR_TYPES.has(star.star_type) && (
        <div className='flex min-w-0 flex-col gap-2'>
          <div className='flex min-w-0 flex-wrap gap-2'>
            <CosmicActionButton
              actionId='cosmic:rekindle_star'
              label='Re-ignite'
              icon={Flame}
              variant='default'
              cost={rules.get('rekindleStar')}
              pending={rekindle.isPending}
              onRun={() => rekindle.mutate()}
            />
          </div>
          <Muted variant='caption'>
            {`The star burns again at brightness ${ruleText(rules.get('rekindleBrightness'))}; leakage of the ${plural(orbiting.length, 'world', 'worlds')} in its orbit drops by ${ruleText(rules.get('rekindleLeak'))}.`}
          </Muted>
        </div>
      )}
      {!DEAD_STAR_TYPES.has(star.star_type) && (
        <div className='flex min-w-0 flex-col gap-2'>
          <div className='flex min-w-0 flex-wrap gap-2'>
            <CosmicActionButton
              actionId='cosmic:extinguish_star'
              label='Extinguish'
              icon={MoonStar}
              variant='destructive'
              cost={rules.get('extinguishStar')}
              pending={extinguish.isPending}
              confirm={{
                title: `Extinguish ${star.name}?`,
                description: `It becomes a dead star. ${orbiting.length === 1 ? 'The world in its orbit cools' : `The ${plural(orbiting.length, 'world', 'worlds')} in its orbit cool`}: leakage rises by ${ruleText(rules.get('extinguishLeak'))}, every region loses ${ruleText(rules.get('extinguishFertility'))} fertility, sail roads to it snap and the end draws ${ruleText(rules.get('extinguishDoom'))} closer. It can be re-ignited later.`,
                confirmText: 'Extinguish',
              }}
              onRun={() => extinguish.mutate()}
            />
          </div>
          <Muted variant='caption'>
            {`Darkness falls on the ${orbiting.length === 1 ? 'world' : `${plural(orbiting.length, 'world', 'worlds')}`} in its orbit; re-igniting it later costs ${ruleText(rules.get('rekindleStar'))} essence.`}
          </Muted>
        </div>
      )}
      <Button
        variant='outline'
        className='self-start'
        onClick={() => drawers.open({ kind: 'star', id: String(star.id) })}
      >
        <BookOpen />
        Lore and history
      </Button>
      <Section title='Worlds in its orbit' level={3}>
        {orbiting.length === 0 ? (
          <Muted>No world around this star yet.</Muted>
        ) : (
          <PagedList
            items={orbiting}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap gap-2'
            itemKey={(item) => item.world.id}
          >
            {(item) => (
              <Button
                key={item.world.id}
                variant='outline'
                size='sm'
                onClick={() => onSelectWorld(item.world.id)}
              >
                {`${item.world.name} · orbit ${formatDecimal(item.world.orbit)}`}
              </Button>
            )}
          </PagedList>
        )}
      </Section>
      <Collapsible className='flex min-w-0 flex-col gap-4 rounded-xl border p-4'>
        <CollapsibleTrigger asChild>
          <Button variant='ghost' className='justify-start'>
            Edit the star
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <StarEditForm key={star.id} star={star} />
        </CollapsibleContent>
      </Collapsible>
      {orbiting.length === 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <div className='flex min-w-0 flex-wrap gap-2'>
            <CosmicActionButton
              actionId='star:delete'
              label='Remove from the sky'
              icon={Trash2}
              variant='destructive'
              pending={remove.isPending}
              confirm={{
                title: `Remove ${star.name}?`,
                description:
                  'No world circles it. The removal can be undone from the ledger.',
                confirmText: 'Remove',
              }}
              onRun={() => remove.mutate()}
            />
          </div>
          <Muted variant='caption'>
            No world around it; this can be undone from the ledger.
          </Muted>
        </div>
      )}
    </article>
  )
}
