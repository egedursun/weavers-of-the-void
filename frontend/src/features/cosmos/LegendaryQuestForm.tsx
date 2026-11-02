import { useState } from 'react'
import { Swords } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FormRow } from '@/components/domain'
import { Muted } from '@/components/typography'
import { CosmicActionButton } from './CosmicActionButton'
import { type LegendaryQuestKind } from './api'
import { type CosmosIndex } from './model/cosmosModel'
import { LEGENDARY_QUESTS, LEGENDARY_QUEST_LABEL } from './model/labels'
import { questBlockers } from './model/quests'
import { type RuleBook } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

export function LegendaryQuestForm({
  index,
  rules,
}: {
  index: CosmosIndex
  rules: RuleBook
}) {
  const blockers = questBlockers(index)
  const available = LEGENDARY_QUESTS.filter(
    (kind) => blockers[kind] === undefined
  )
  const [choice, setChoice] = useState<LegendaryQuestKind | ''>('')
  const kind: LegendaryQuestKind | '' = choice || available.at(0) || ''
  const proclaim = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/cosmic/legendary-quest', {
          body: { kind: kind as LegendaryQuestKind },
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
      <FormRow label='Quest'>
        {(id) => (
          <Select
            value={kind}
            onValueChange={(value) => setChoice(value as LegendaryQuestKind)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue placeholder='No quest has a target' />
            </SelectTrigger>
            <SelectContent>
              {LEGENDARY_QUESTS.map((value) => (
                <SelectItem
                  key={value}
                  value={value}
                  disabled={blockers[value] !== undefined}
                >
                  {blockers[value]
                    ? `${LEGENDARY_QUEST_LABEL[value]} · ${blockers[value]}`
                    : LEGENDARY_QUEST_LABEL[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <CosmicActionButton
          actionId='cosmic:legendary_quest'
          label='Proclaim'
          icon={Swords}
          variant='default'
          cost={rules.get('legendaryQuest')}
          pending={proclaim.isPending}
          blockedReason={
            kind === ''
              ? 'No legendary quest currently has a target.'
              : undefined
          }
          onRun={() => proclaim.mutate()}
        />
      </div>
    </div>
  )
}
