import { useState } from 'react'
import { ThermometerSun } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Input } from '@/components/ui/input'
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
import { type ClimateEra } from './api'
import { type CosmosIndex } from './model/cosmosModel'
import { CLIMATE_ERAS, CLIMATE_LABEL } from './model/labels'
import { type RuleBook, ruleText } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

const ALL = 'all'

export function ClimateCycleForm({
  index,
  rules,
}: {
  index: CosmosIndex
  rules: RuleBook
}) {
  const [world, setWorld] = useState(ALL)
  const [era, setEra] = useState<ClimateEra>('rain')
  const [epochs, setEpochs] = useState('')
  const cap = rules.get('climateMaxEpochs')
  const fallback = rules.get('climateEpochs')
  const parsed = epochs.trim() === '' ? undefined : Number(epochs)
  const invalid =
    parsed !== undefined &&
    (!Number.isInteger(parsed) ||
      parsed < 1 ||
      (cap !== undefined && parsed > cap))
  const command = useCosmicAction({
    run: () =>
      unwrap(
        api.PUT('/api/climate', {
          body: {
            era,
            ...(parsed === undefined ? {} : { epochs: parsed }),
            ...(world === ALL ? {} : { world_id: Number(world) }),
          },
        })
      ),
    success: 'A new cycle was commanded to the sky',
  })
  const worlds = index.worlds.filter(
    (item) => item.world.discovery !== 'forgotten'
  )
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <FormRow label='World'>
        {(id) => (
          <Select value={world} onValueChange={setWorld}>
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All worlds</SelectItem>
              {worlds.map((item) => (
                <SelectItem key={item.world.id} value={String(item.world.id)}>
                  {`${item.world.name} · now ${item.world.climate_era ? CLIMATE_LABEL[item.world.climate_era] : 'mild'}`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow label='Climate'>
        {(id) => (
          <Select
            value={era}
            onValueChange={(value) => setEra(value as ClimateEra)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {CLIMATE_ERAS.map((value) => (
                <SelectItem key={value} value={value}>
                  {CLIMATE_LABEL[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow
        label='Epochs'
        description={`1 to ${ruleText(cap)}; blank uses ${ruleText(fallback)}.`}
      >
        {(id) => (
          <Input
            id={id}
            type='number'
            min={1}
            max={cap}
            inputMode='numeric'
            placeholder={ruleText(fallback)}
            value={epochs}
            aria-invalid={invalid || undefined}
            onChange={(event) => setEpochs(event.target.value)}
          />
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <CosmicActionButton
          actionId='climate'
          label='Start the cycle'
          icon={ThermometerSun}
          variant='default'
          pending={command.isPending}
          blockedReason={
            invalid
              ? `Enter a whole number from 1 to ${ruleText(cap)}.`
              : undefined
          }
          onRun={() => command.mutate()}
        />
      </div>
      <Muted variant='caption'>
        Each world keeps its own climate; it returns to its old way when the
        cycle ends.
      </Muted>
    </div>
  )
}
