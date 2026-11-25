import { useState } from 'react'
import {
  CloudFog,
  Eye,
  Flame,
  Map as MapIcon,
  RotateCcw,
  ShieldCheck,
  Skull,
  Sparkles,
  Sprout,
  Sun,
  SunDim,
  Users,
  Waves,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Section, FieldTile } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { useSons } from '@/features/pantheon/api'
import { CosmicActionButton } from './CosmicActionButton'
import { type ActionResponse, type CosmosWorld, type Disaster } from './api'
import { DISASTERS, DISASTER_LABEL } from './model/labels'
import { type RuleBook, ruleText } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

type CreatorHandPanelProps = {
  item: CosmosWorld
  isHome: boolean
  rules: RuleBook
}

export function CreatorHandPanel({
  item,
  isHome,
  rules,
}: CreatorHandPanelProps) {
  const world = item.world
  const worldId = world.id
  const forgotten = world.discovery === 'forgotten'
  const [disaster, setDisaster] = useState<Disaster>('earthquake')
  const cleanse = useCosmicAction({
    writes: [{ lever: 'cosmic:cleanse_leak' }],
    run: () =>
      unwrap(
        api.POST('/api/cosmic/cleanse-leak', { body: { world_id: worldId } })
      ),
    success: 'Leakage cleansed',
  })
  const forget = useCosmicAction({
    writes: [{ lever: 'cosmic:forget_world' }],
    run: () =>
      unwrap(
        api.POST('/api/cosmic/forget-world', { body: { world_id: worldId } })
      ),
    success: `${world.name} was buried in oblivion`,
  })
  const remember = useCosmicAction({
    writes: [{ lever: 'world:edit' }],
    run: () =>
      unwrap(
        api.PATCH('/api/worlds/{world_id}', {
          params: { path: { world_id: worldId } },
          body: { discovery: 'known', automatic_mortal_agents: false },
        })
      ),
    success: `${world.name} is remembered again`,
  })
  const wrath = useCosmicAction({
    writes: [{ lever: 'wrath:world' }],
    run: () =>
      unwrap(
        api.POST('/api/worlds/{world_id}/wrath', {
          params: { path: { world_id: worldId } },
          body: { disaster },
        })
      ),
    success: `${world.name} tasted wrath`,
  })
  const order = useCosmicAction({
    writes: [
      { lever: 'awaken_peoples' },
      { lever: 'horror:outer_being' },
      { lever: 'species:seed' },
      { lever: 'world:end_golden_age' },
      { lever: 'world:golden_age' },
      { lever: 'world:guardian' },
      { lever: 'world:map' },
      { lever: 'world:planet_stirs' },
      { lever: 'world:previous_creation' },
      { lever: 'world:revive' },
    ],
    run: (call: () => Promise<ActionResponse>) => call(),
  })
  const target = { body: { world_id: worldId } }
  const sons = (useSons().data ?? []).filter(
    (view) => view.son.status !== 'dead'
  )
  const [guardian, setGuardian] = useState<string>('')
  const awakenCount = rules.path('awakening.first_peoples')
  return (
    <Section title="Creator's hand · cosmic actions" level={3} surface='card'>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <CosmicActionButton
          act={cleanse}
          actionId='cosmic:cleanse_leak'
          label='Cleanse leakage'
          icon={Waves}
          cost={rules.get('cleanseLeak')}
          pending={cleanse.isPending}
          onRun={() => cleanse.mutate()}
        />
        {!isHome && !forgotten && (
          <CosmicActionButton
            act={forget}
            actionId='cosmic:forget_world'
            label='Bury in oblivion'
            icon={CloudFog}
            variant='destructive'
            cost={rules.get('forgetWorld')}
            pending={forget.isPending}
            confirm={{
              title: `Bury ${world.name} in oblivion?`,
              description:
                'The world is wrapped in mist and every route to it closes.',
              confirmText: 'Bury in mist',
            }}
            onRun={() => forget.mutate()}
          />
        )}
        {forgotten && (
          <CosmicActionButton
            act={remember}
            actionId='world:edit'
            label='Remember this world'
            icon={Eye}
            pending={remember.isPending}
            onRun={() => remember.mutate()}
          />
        )}
      </div>
      <Muted variant='caption'>
        {world.leakage > 0
          ? `Cleansing lowers leakage by ${ruleText(rules.get('cleanseAmount'))} and may expel Outsiders. `
          : 'No leakage here; cleansing can still expel an Outsider hiding inside. '}
        {isHome
          ? 'The first world cannot be buried in oblivion: it is the home the pantheon and the sons return to.'
          : forgotten
            ? 'This world is already in oblivion; remembering it brings it back, its routes stay closed until reopened.'
            : 'Oblivion hides the world and closes all its routes.'}
      </Muted>
      {!forgotten && (
        <div className='flex min-w-0 flex-col gap-2'>
          <FieldTile group label='World wrath'>
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Select
                value={disaster}
                onValueChange={(value) => setDisaster(value as Disaster)}
              >
                <SelectTrigger
                  aria-label='Disaster'
                  className='w-full sm:w-auto'
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DISASTERS.map((kind) => (
                    <SelectItem key={kind} value={kind}>
                      {DISASTER_LABEL[kind]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <CosmicActionButton
                act={wrath}
                actionId='wrath:world'
                label='Bring down on the whole world'
                icon={Flame}
                variant='destructive'
                cost={rules.get('worldWrathCost')}
                pending={wrath.isPending}
                confirm={{
                  title: `Shake all of ${world.name}?`,
                  description: `${DISASTER_LABEL[disaster]} strikes every region at ${ruleText(rules.get('worldWrathSeverity'))}% severity.`,
                  confirmText: 'Bring it down',
                }}
                onRun={() => wrath.mutate()}
              />
            </div>
          </FieldTile>
        </div>
      )}
      <div className='flex min-w-0 flex-col gap-2'>
        <Label>World orders</Label>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            act={order}
            actionId='awaken_peoples'
            label='Awaken peoples'
            icon={Users}
            size='sm'
            pending={order.isPending}
            blockedReason={
              awakenCount === undefined
                ? 'The awakening rules are still loading.'
                : undefined
            }
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/peoples/awaken', {
                    body: { world_id: worldId, count: awakenCount ?? 0 },
                  })
                )
              )
            }
          />
          <CosmicActionButton
            act={order}
            actionId='world:golden_age'
            label='Proclaim a golden age'
            icon={Sun}
            size='sm'
            pending={order.isPending}
            onRun={() =>
              order.mutate(() =>
                unwrap(api.POST('/api/actions/world:golden_age', target))
              )
            }
          />
          <CosmicActionButton
            act={order}
            actionId='world:end_golden_age'
            label='End the golden age'
            icon={SunDim}
            size='sm'
            pending={order.isPending}
            onRun={() =>
              order.mutate(() =>
                unwrap(api.POST('/api/actions/world:end_golden_age', target))
              )
            }
          />
          <CosmicActionButton
            act={order}
            actionId='world:map'
            label='Redraw its map'
            icon={MapIcon}
            size='sm'
            pending={order.isPending}
            onRun={() =>
              order.mutate(() =>
                unwrap(api.POST('/api/actions/world:map', target))
              )
            }
          />
          <CosmicActionButton
            act={order}
            actionId='world:previous_creation'
            label='Reveal a previous creation'
            icon={Sparkles}
            size='sm'
            pending={order.isPending}
            onRun={() =>
              order.mutate(() =>
                unwrap(api.POST('/api/actions/world:previous_creation', target))
              )
            }
          />
          {world.world_type === 'living' && (
            <CosmicActionButton
              act={order}
              actionId='world:planet_stirs'
              label='Make the planet stir'
              icon={Sprout}
              size='sm'
              pending={order.isPending}
              onRun={() =>
                order.mutate(() =>
                  unwrap(api.POST('/api/actions/world:planet_stirs', target))
                )
              }
            />
          )}
          <CosmicActionButton
            act={order}
            actionId='horror:outer_being'
            label='Summon an outer being'
            icon={Skull}
            size='sm'
            variant='destructive'
            pending={order.isPending}
            confirm={{
              title: `Let an outer being into ${world.name}?`,
              description:
                'A thing from outside takes shape in this world. Leakage and dread follow it.',
              confirmText: 'Summon',
            }}
            onRun={() =>
              order.mutate(() =>
                unwrap(api.POST('/api/actions/horror:outer_being', target))
              )
            }
          />
          <CosmicActionButton
            act={order}
            actionId='species:seed'
            label='Seed native life'
            icon={Sprout}
            size='sm'
            pending={order.isPending}
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/species:seed', {
                    body: { world_id: worldId, people: false },
                  })
                )
              )
            }
          />
          <CosmicActionButton
            act={order}
            actionId='species:seed'
            label='Raise a native people'
            icon={Users}
            size='sm'
            pending={order.isPending}
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/species:seed', {
                    body: { world_id: worldId, people: true },
                  })
                )
              )
            }
          />
          <CosmicActionButton
            act={order}
            actionId='world:revive'
            label='Revive this world'
            icon={RotateCcw}
            size='sm'
            pending={order.isPending}
            onRun={() =>
              order.mutate(() =>
                unwrap(api.POST('/api/actions/world:revive', target))
              )
            }
          />
        </div>
      </div>
      <div className='flex min-w-0 flex-col gap-2'>
        <FieldTile group label='Guardian'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Select value={guardian} onValueChange={setGuardian}>
              <SelectTrigger
                aria-label='Guardian son'
                className='w-full sm:w-60'
              >
                <SelectValue placeholder='Choose a son' />
              </SelectTrigger>
              <SelectContent>
                {sons.map((view) => (
                  <SelectItem key={view.son.id} value={String(view.son.id)}>
                    {view.son.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <CosmicActionButton
              act={order}
              actionId='world:guardian'
              label='Appoint as guardian'
              icon={ShieldCheck}
              size='sm'
              pending={order.isPending}
              blockedReason={
                guardian === '' ? 'Choose a son first.' : undefined
              }
              onRun={() =>
                order.mutate(() =>
                  unwrap(
                    api.POST('/api/actions/world:guardian', {
                      body: { world_id: worldId, son_id: Number(guardian) },
                    })
                  )
                )
              }
            />
          </div>
        </FieldTile>
      </div>
    </Section>
  )
}
