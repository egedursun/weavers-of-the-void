import { useState } from 'react'
import { Telescope, Trash2 } from 'lucide-react'
import { type ActionBody } from '@/api/actions'
import { type ActProp } from '@/api/mutation'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { EmptyState, EntityLink, PagedList, Section } from '@/components/domain'
import {
  Chip,
  ForgeCard,
  RecordPick,
  RecordRow,
} from '@/features/cosmography/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import {
  type SurveyRecord,
  physicsKeys,
  usePhysicsAction,
  useObserverSurveys,
  useWorldPhysics,
} from './api'
import { SURVEY_LEVELS, table } from './labels'
import { QuerySection, WorldPicker } from './parts'

type Set = { observer: number; world: number; level: string }

function SurveyList({
  rows,
  by,
  busy,
  onForget,
  act,
}: {
  rows: readonly SurveyRecord[]
  by: 'observer' | 'world'
  busy: string | null
  onForget: (id: number) => void
  act?: ActProp
}) {
  if (rows.length === 0)
    return (
      <EmptyState
        icon={Telescope}
        size='inline'
        title={
          by === 'observer'
            ? 'No people or realm of another world knows it yet'
            : 'It knows no world beyond its own'
        }
        description='Astronomy, sky navigation and journeys bring knowledge of the worlds; you can also grant it below.'
      />
    )
  return (
    <PagedList
      items={[...rows]}
      initial={8}
      noun={['world', 'worlds']}
      className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
      itemKey={(row) => String(row.id)}
    >
      {(row) => {
        const subject = by === 'observer' ? row.observer : row.world
        return (
          <RecordRow
            icon={SURVEY_LEVELS[row.level].icon}
            tone={SURVEY_LEVELS[row.level].tone}
            title={
              subject ? (
                <EntityLink
                  kind={by === 'observer' ? 'entity' : 'world'}
                  id={String(subject.id)}
                >
                  {subject.name}
                </EntityLink>
              ) : (
                'Unknown'
              )
            }
            caption={`${SURVEY_LEVELS[row.level].label} since epoch ${row.epoch}${row.locked.includes('level') ? ' · held' : ''}`}
            aside={
              <Button
                act={act}
                size='sm'
                variant='ghost'
                aria-label='Make them forget it'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => onForget(row.id)}
              >
                <Trash2 />
              </Button>
            }
          />
        )
      }}
    </PagedList>
  )
}

function useSurveyActions(refresh: readonly (readonly unknown[])[]) {
  const set = usePhysicsAction(
    'survey:set',
    (vars: Set) => ({
      observer_id: vars.observer,
      world_id: vars.world,
      level: vars.level as ActionBody<'survey:set'>['level'],
    }),
    'What they know of the world is set',
    refresh
  )
  const forget = usePhysicsAction(
    'survey:forget',
    (survey: number) => ({ survey_id: survey }),
    'They forget the world',
    refresh
  )
  return {
    set,
    forget,
    busy:
      set.blockedReason ??
      forget.blockedReason ??
      (set.isPending || forget.isPending ? 'Working' : null),
  }
}

export function WorldSurveySection({ worldId }: { worldId: number }) {
  const query = useWorldPhysics(worldId)
  const { set, forget, busy } = useSurveyActions([physicsKeys.world(worldId)])
  const [observer, setObserver] = useState<number | null>(null)
  const [level, setLevel] = useState('')
  const missing =
    observer === null
      ? 'Choose a people or realm first'
      : level === ''
        ? 'Choose how well they know it first'
        : null
  return (
    <QuerySection
      id='section-surveys'
      title='Who knows this world'
      description='How well the peoples and realms of other worlds know this one; journeys, colonies and conquests each need it known well enough.'
      icon={Telescope}
      tone='info'
      query={query}
    >
      {(view) => (
        <div className='flex min-w-0 flex-col gap-3'>
          <SurveyList
            act={forget}
            rows={view.surveys}
            by='observer'
            busy={busy}
            onForget={(id) => forget.mutate(id)}
          />
          <ForgeCard
            icon={Telescope}
            tone='info'
            title='Grant knowledge of this world'
            note='The level you set is held against the engine.'
            columns={2}
            meta={
              <Chip
                icon={Telescope}
              >{`${plural(view.surveys.length, 'people or realm', 'peoples or realms')} ${view.surveys.length === 1 ? 'knows' : 'know'} it`}</Chip>
            }
            action={
              <Button
                act={set}
                size='sm'
                disabled={busy !== null || missing !== null}
                disabledReason={busy ?? missing ?? undefined}
                onClick={() =>
                  observer !== null &&
                  set.mutate({ observer, world: worldId, level })
                }
              >
                <Telescope />
                Set it
              </Button>
            }
          >
            <RecordPick
              label='People or realm'
              types={['people', 'polity']}
              value={observer}
              onChange={setObserver}
            />
            <MindPicker
              label='How well'
              value={level}
              table={table(SURVEY_LEVELS)}
              blocked={busy}
              onPick={setLevel}
            />
          </ForgeCard>
        </div>
      )}
    </QuerySection>
  )
}

export function ObserverSurveySection({ observerId }: { observerId: number }) {
  const query = useObserverSurveys(observerId)
  const { set, forget, busy } = useSurveyActions([
    physicsKeys.observer(observerId),
  ])
  const [world, setWorld] = useState('')
  const [level, setLevel] = useState('')
  const missing =
    world === ''
      ? 'Choose a world first'
      : level === ''
        ? 'Choose how well they know it first'
        : null
  return (
    <Section
      id='section-known-worlds'
      title='Worlds it knows'
      description='How well it knows each world beyond its own.'
      icon={Telescope}
      tone='info'
    >
      {query.isError ? (
        <EmptyState
          icon={Telescope}
          size='inline'
          title='Its knowledge could not be read'
          description={query.error.message}
        />
      ) : (
        <div className='flex min-w-0 flex-col gap-3'>
          <SurveyList
            act={forget}
            rows={query.data?.surveys ?? []}
            by='world'
            busy={busy}
            onForget={(id) => forget.mutate(id)}
          />
          <ForgeCard
            icon={Telescope}
            tone='info'
            title='Grant knowledge of a world'
            note='The level you set is held against the engine.'
            columns={2}
            action={
              <Button
                act={set}
                size='sm'
                disabled={busy !== null || missing !== null}
                disabledReason={busy ?? missing ?? undefined}
                onClick={() =>
                  set.mutate({
                    observer: observerId,
                    world: Number(world),
                    level,
                  })
                }
              >
                <Telescope />
                Set it
              </Button>
            }
          >
            <WorldPicker value={world} onPick={setWorld} busy={busy} />
            <MindPicker
              label='How well'
              value={level}
              table={table(SURVEY_LEVELS)}
              blocked={busy}
              onPick={setLevel}
            />
          </ForgeCard>
        </div>
      )}
    </Section>
  )
}
