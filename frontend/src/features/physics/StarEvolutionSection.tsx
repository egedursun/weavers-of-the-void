import { Flame, Hourglass, Sparkles, Star } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { Facts, NodeLink, RecordEditor } from '@/features/cosmography/parts'
import { STAR_TYPE_LABEL } from '@/features/cosmos/model/labels'
import { useSons } from '@/features/pantheon/api'
import {
  type StarPhysicsView,
  physicsKeys,
  usePhysicsAction,
  useStarPhysics,
} from './api'
import { fixed } from './format'
import { STAR_STAGES } from './labels'
import { QuerySection } from './parts'

const BODY_KEYS = [
  'mass',
  'metallicity',
  'age_epochs',
  'upkeep',
  'maker_son_id',
]

type Edit = {
  values?: EditValues
  release?: string[]
}

function Track({ view }: { view: StarPhysicsView }) {
  return (
    <ol
      className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4'
      aria-label='Stages of its life'
    >
      <Paged items={view.stages} as='li'>
        {(span) => {
          const now = span.stage === view.age_stage
          return (
            <li
              key={span.stage}
              aria-current={now ? 'step' : undefined}
              className={cn(
                'flex min-w-0 flex-col gap-0.5 rounded-md border surface-sheen border-gild/60 bg-card p-2',
                now ? 'border-primary bg-primary/10' : 'bg-muted/30'
              )}
            >
              <Text as='span' weight='semibold'>
                {STAR_STAGES[span.stage]}
              </Text>
              <Muted as='span' variant='caption'>
                {`${plural(span.epochs, 'epoch', 'epochs')}`}
              </Muted>
            </li>
          )
        }}
      </Paged>
    </ol>
  )
}

export function StarEvolutionSection({ starId }: { starId: number }) {
  const query = useStarPhysics(starId)
  const sons = useSons()
  const makers = Object.fromEntries(
    (sons.data ?? []).map((view) => [String(view.son.id), view.son.name])
  )
  const edit = usePhysicsAction(
    'star_physics:edit',
    (vars: Edit) => ({
      star_id: starId,
      values: vars.values ?? {},
      release: vars.release ?? [],
    }),
    'The star is reshaped',
    [physicsKeys.star(starId)]
  )
  const busy = edit.isPending ? 'Working' : null
  return (
    <QuerySection
      id='section-star-evolution'
      title='How the star ages'
      description='How its mass sets its light, the length of each stage and how it ends.'
      icon={Star}
      tone='gold'
      query={query}
    >
      {(view) => (
        <div className='flex min-w-0 flex-col gap-3'>
          <div className='flex min-w-0 flex-wrap gap-1'>
            <Badge size='sm' variant='outline'>
              <Hourglass />
              {`Age ${plural(view.age_epochs, 'epoch', 'epochs')}`}
            </Badge>
            {view.supernova && (
              <Badge size='sm' variant='destructive'>
                <Flame />
                Ends in a supernova
              </Badge>
            )}
            {view.maker && (
              <Badge size='sm' variant='info'>
                <Sparkles />
                {`Made outside its kind's laws: ${view.upkeep} essence each epoch`}
              </Badge>
            )}
          </div>
          <Track view={view} />
          <Facts
            items={[
              ['Mass', `${fixed(view.mass)} suns`],
              ['Metal', `${view.metallicity}/100`],
              ['Light', `${fixed(view.luminosity, 3)} suns`],
              [
                'Main life',
                `${plural(view.lifetime_epochs, 'epoch', 'epochs')}`,
              ],
              [
                'Temperate band',
                `${fixed(view.band_inner)} to ${fixed(view.band_outer)} orbits`,
              ],
              [
                'Swells into',
                view.giant ? STAR_TYPE_LABEL[view.giant] : 'Never swells',
              ],
              [
                'Swallows worlds within',
                view.giant ? `${fixed(view.engulf_orbit)} orbits` : 'None',
              ],
              ['Leaves behind', STAR_TYPE_LABEL[view.remnant]],
              [
                'Made by',
                <NodeLink
                  key='maker'
                  kind='son'
                  id={view.maker?.id}
                  name={view.maker?.name ?? 'Its own kind'}
                />,
              ],
            ]}
          />
          <div className='flex min-w-0 flex-col gap-1'>
            <Label>Reshape its body</Label>
            <RecordEditor
              act={edit}
              title='Mass, metal, age and upkeep'
              note='Mass sets its light and how long each stage lasts; a held value is kept against the engine.'
              fields={[
                {
                  key: 'mass',
                  label: 'Mass (suns)',
                  kind: 'decimal',
                  min: 0.01,
                },
                {
                  key: 'metallicity',
                  label: 'Metal',
                  kind: 'number',
                  min: 0,
                  max: 100,
                },
                {
                  key: 'age_epochs',
                  label: 'Age (epochs)',
                  kind: 'number',
                  min: 0,
                },
                {
                  key: 'upkeep',
                  label: 'Upkeep (essence)',
                  kind: 'number',
                  min: 0,
                },
                {
                  key: 'maker_son_id',
                  label: 'Maker who keeps it',
                  kind: 'pick',
                  table: makers,
                },
              ]}
              locked={view.locked.filter((key) => BODY_KEYS.includes(key))}
              busy={busy}
              onSave={(values) =>
                edit.mutate({
                  values,
                })
              }
              onRelease={(release) => edit.mutate({ release })}
            />
            <RecordEditor
              act={edit}
              title='Light, life and temperate band'
              note='Its mass works these out each epoch; a value you hold here stands by your will.'
              fields={[
                {
                  key: 'luminosity',
                  label: 'Light (suns)',
                  kind: 'decimal',
                  min: 0,
                },
                {
                  key: 'lifetime_epochs',
                  label: 'Main life (epochs)',
                  kind: 'number',
                  min: 0,
                },
                {
                  key: 'band_inner',
                  label: 'Temperate band from (orbits)',
                  kind: 'decimal',
                  min: 0,
                },
                {
                  key: 'band_outer',
                  label: 'Temperate band to (orbits)',
                  kind: 'decimal',
                  min: 0,
                },
              ]}
              locked={view.locked.filter((key) => !BODY_KEYS.includes(key))}
              busy={busy}
              onSave={(values) => edit.mutate({ values })}
              onRelease={(release) => edit.mutate({ release })}
            />
          </div>
        </div>
      )}
    </QuerySection>
  )
}
