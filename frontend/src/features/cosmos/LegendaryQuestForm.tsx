import { useState } from 'react'
import { Swords } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FormRow } from '@/components/domain'
import { Muted } from '@/components/typography'
import {
  AIMS,
  OBSTACLES,
  QUEST_TARGETS,
  REWARDS,
} from '@/features/typedModels/labels'
import { ChoiceField } from '@/features/wars/military/parts'
import { CosmicActionButton } from './CosmicActionButton'
import { type QuestAim } from './api'
import { type CosmosIndex } from './model/cosmosModel'
import {
  LEGENDARY_AIMS,
  LEGENDARY_TARGETS,
  type LegendaryTarget,
  questBlockers,
} from './model/quests'
import { type RuleBook } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

type QuestObstacle = components['schemas']['QuestObstacle']
type QuestReward = components['schemas']['QuestReward']

export function LegendaryQuestForm({
  index,
  rules,
}: {
  index: CosmosIndex
  rules: RuleBook
}) {
  const blockers = questBlockers(index)
  const open = LEGENDARY_TARGETS.filter((item) => blockers[item] === undefined)
  const [choice, setChoice] = useState<LegendaryTarget | ''>('')
  const target: LegendaryTarget | '' = choice || open.at(0) || ''
  const [aim, setAim] = useState<QuestAim | ''>('')
  const [obstacle, setObstacle] = useState<string>('distance')
  const [reward, setReward] = useState<string>('renown')
  const aims = target === '' ? [] : LEGENDARY_AIMS[target]
  const chosenAim = aim !== '' && aims.includes(aim) ? aim : aims.at(0)
  const proclaim = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/cosmic/legendary-quest', {
          body: {
            target_kind: target as LegendaryTarget,
            aim: chosenAim ?? 'restore',
            obstacle: obstacle as QuestObstacle,
            reward: reward as QuestReward,
          },
        })
      ),
    success: 'Legendary quest proclaimed; Fate will follow it as a story',
  })
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Muted>
        A quest that the peoples and the sons will remember. It runs for several
        epochs and earns essence and hope when it succeeds.
      </Muted>
      <FormRow label='What it seeks'>
        {(id) => (
          <Select
            value={target}
            onValueChange={(value) => setChoice(value as LegendaryTarget)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue placeholder='No quest has a target' />
            </SelectTrigger>
            <SelectContent>
              {LEGENDARY_TARGETS.map((value) => (
                <SelectItem
                  key={value}
                  value={value}
                  disabled={blockers[value] !== undefined}
                >
                  {blockers[value]
                    ? `${QUEST_TARGETS[value].label} · ${blockers[value]}`
                    : QUEST_TARGETS[value].label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
        <ChoiceField
          label='Aim'
          value={chosenAim ?? ''}
          table={Object.fromEntries(aims.map((item) => [item, AIMS[item]]))}
          blocked={target === '' ? 'Choose what it seeks first' : null}
          onPick={(value) => setAim(value as QuestAim)}
        />
        <ChoiceField
          label='What stands in the way'
          value={obstacle}
          table={OBSTACLES}
          blocked={null}
          onPick={setObstacle}
        />
        <ChoiceField
          label='Reward'
          value={reward}
          table={REWARDS}
          blocked={null}
          onPick={setReward}
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <CosmicActionButton
          actionId='cosmic:legendary_quest'
          label='Proclaim'
          icon={Swords}
          variant='default'
          cost={rules.get('legendaryQuest')}
          pending={proclaim.isPending}
          blockedReason={
            target === ''
              ? 'No legendary quest currently has a target.'
              : undefined
          }
          onRun={() => proclaim.mutate()}
        />
      </div>
    </div>
  )
}
