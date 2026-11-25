import { useState } from 'react'
import {
  Cpu,
  Hand,
  Landmark,
  Save,
  Scale,
  Settings2,
  Sparkles,
  Users,
  Wand2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Section } from '@/components/domain'
import {
  type Choice,
  ChoiceTiles,
  SettingGroup,
  SettingRow,
  SwitchRow,
} from '@/components/domain/SettingsKit'
import { Text } from '@/components/typography'
import { toastDone } from '@/features/team/outcome'
import { type WorldSettings, usePatchSettings } from './api'
import { type Draft, draftOf, patchFrom } from './worldSettingsModel'

const DISTRIBUTIONS: readonly Choice<Draft['distribution']>[] = [
  {
    value: 'auto',
    label: 'Automatic',
    hint: 'Sons go wherever no god watches',
    icon: Sparkles,
  },
  {
    value: 'manual',
    label: 'Manual',
    hint: 'Only you send them',
    icon: Hand,
  },
]

type WorldSettingsFormProps = {
  settings: WorldSettings
  readOnly: boolean
}

export function WorldSettingsForm({
  settings,
  readOnly,
}: WorldSettingsFormProps) {
  const patch = usePatchSettings()
  const [draft, setDraft] = useState(() => draftOf(settings))
  const [error, setError] = useState<string | null>(null)
  const update = (next: Partial<Draft>) => {
    setError(null)
    setDraft((current) => ({ ...current, ...next }))
  }
  const save = () => {
    const body = patchFrom(settings, draft)
    if (typeof body === 'string') {
      setError(body)
      return
    }
    patch.mutate(body, {
      onSuccess: (result) =>
        toastDone(result, result.message || 'Settings saved'),
      onError: (failure) => setError(failure.message),
    })
  }
  const councilOff = Number(draft.council) === 0
  return (
    <Section
      title='Fate, sons and mortals'
      description='How the world runs itself each epoch. Every change is written to the ledger and can be undone.'
      surface='card'
      icon={Settings2}
      actions={
        <Button
          act={patch}
          onClick={save}
          disabled={readOnly || patch.isPending}
          disabledReason={readOnly ? 'A guest world is read-only' : 'Saving'}
        >
          <Save />
          Save settings
        </Button>
      }
    >
      <SwitchRow
        icon={Scale}
        tone='warning'
        label='Fate judges'
        description='Fate rejects inconsistent creations at the end of each epoch.'
        checked={draft.fateAuto}
        onChange={(checked) => update({ fateAuto: checked })}
      />
      <SettingGroup
        label='Son distribution'
        description='Whether sons settle godless worlds by themselves.'
      >
        <ChoiceTiles
          label='Son distribution'
          value={draft.distribution}
          options={DISTRIBUTIONS}
          onChange={(value) => update({ distribution: value })}
          columns={2}
        />
      </SettingGroup>
      <div className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'>
        <SettingRow
          icon={Landmark}
          label='Council every'
          description={
            councilOff
              ? 'Automatic councils are off.'
              : 'Epochs between automatic councils; 0 turns them off.'
          }
          active={!councilOff}
        >
          {(id) => (
            <Input
              id={id}
              type='number'
              min={0}
              inputMode='numeric'
              value={draft.council}
              onChange={(event) => update({ council: event.target.value })}
              className='w-28'
            />
          )}
        </SettingRow>
        <SettingRow
          icon={Cpu}
          tone='info'
          label='Thinking at once'
          description='More is faster but spends the model quota sooner.'
        >
          {(id) => (
            <Input
              id={id}
              type='number'
              min={1}
              inputMode='numeric'
              value={draft.parallelism}
              onChange={(event) => update({ parallelism: event.target.value })}
              className='w-28'
            />
          )}
        </SettingRow>
        <SwitchRow
          icon={Wand2}
          tone='verdigris'
          label='Mortal agents chosen automatically'
          description='The world picks how many communities act each epoch.'
          checked={draft.automaticMortals}
          onChange={(checked) => update({ automaticMortals: checked })}
        />
        {!draft.automaticMortals && (
          <SettingRow
            icon={Users}
            tone='verdigris'
            label='Mortal agents per epoch'
            description='The total for the whole cosmos; 0 means none.'
          >
            {(id) => (
              <Input
                id={id}
                type='number'
                min={0}
                inputMode='numeric'
                value={draft.mortals}
                onChange={(event) => update({ mortals: event.target.value })}
                className='w-28'
              />
            )}
          </SettingRow>
        )}
      </div>
      {error && (
        <Text tone='destructive' role='alert'>
          {error}
        </Text>
      )}
    </Section>
  )
}
