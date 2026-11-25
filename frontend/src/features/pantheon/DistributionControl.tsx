import { Shuffle } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { FormRow } from '@/components/domain'
import { ActionButton } from './ActionButton'
import { DistributionPreviewPanel } from './DistributionPreview'
import { godKeys, useWorldState } from './api'
import { useGodGate, useRuleLookup } from './gate'
import { useGodAction } from './godAction'

type Distribution = components['schemas']['SonDistribution']

export function DistributionControl() {
  const state = useWorldState()
  const rule = useRuleLookup()
  const { reason } = useGodGate()
  const mode = state.data?.world?.son_distribution
  const protection = rule('god_hand.assignment_protection_epochs')
  const setMode = useGodAction({
    writes: [{ lever: 'settings' }],
    run: (value: Distribution) =>
      unwrap(
        api.PATCH('/api/settings', {
          body: { son_distribution: value, automatic_mortal_agents: false },
        })
      ),
    success: (_result, value) =>
      value === 'auto'
        ? 'Sons are distributed automatically'
        : 'Sons stay where you send them',
    invalidate: [godKeys.settings],
  })
  const distribute = useGodAction({
    writes: [{ lever: 'son:distribute' }],
    run: () => unwrap(api.POST('/api/sons/distribute')),
    success: 'Sons were sent to the godless worlds',
  })
  if ((state.data?.worlds.length ?? 0) < 2 || !mode) return null
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <FormRow
        label='Distribution of sons'
        description={
          mode === 'auto'
            ? `Each epoch Fate sends sons to godless worlds; a son you send by hand is spared${protection !== undefined ? ` for ${plural(protection, 'epoch', 'epochs')}` : ''}.`
            : 'Sons stay on the worlds you send them to.'
        }
      >
        {(id) => (
          <>
            <ToggleGroup
              act={setMode}
              id={id}
              type='single'
              variant='outline'
              value={mode}
              onValueChange={(value) =>
                value && value !== mode && setMode.mutate(value as Distribution)
              }
            >
              <ToggleGroupItem value='auto'>Automatic</ToggleGroupItem>
              <ToggleGroupItem value='manual'>By hand</ToggleGroupItem>
            </ToggleGroup>
            <ActionButton
              act={distribute}
              label='Distribute now'
              icon={Shuffle}
              blocked={reason()}
              pending={distribute.isPending}
              onRun={() => distribute.mutate()}
            />
          </>
        )}
      </FormRow>
      <DistributionPreviewPanel worlds={state.data?.worlds ?? []} />
    </div>
  )
}
