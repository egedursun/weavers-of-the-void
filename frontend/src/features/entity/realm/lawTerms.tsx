import type { components } from '@/api/generated/schema'
import { Switch } from '@/components/ui/switch'
import { Text } from '@/components/typography'
import { MindPicker } from '../mind/parts'
import { LAW_PARAMS, plain, sentence } from './labels'
import { NumberField } from './parts'

type LawParamSpec = components['schemas']['LawParamSpec']

export function ParamField({
  spec,
  value,
  onChange,
  blocked,
}: {
  spec: LawParamSpec
  value: string | number | boolean
  onChange: (value: string | number | boolean) => void
  blocked: string | null
}) {
  const label = plain(LAW_PARAMS, spec.key)
  if (spec.kind === 'bool')
    return (
      <label className='flex min-w-0 items-center gap-2 self-end rounded-lg border bg-background p-2'>
        <Switch
          checked={Boolean(value)}
          disabled={blocked !== null}
          onCheckedChange={onChange}
          aria-label={label}
        />
        <Text as='span' truncate>
          {label}
        </Text>
      </label>
    )
  if (spec.kind === 'choice')
    return (
      <MindPicker
        label={label}
        value={String(value)}
        table={Object.fromEntries(
          spec.choices.map((choice) => [choice, sentence(choice)])
        )}
        blocked={blocked}
        onPick={onChange}
      />
    )
  return (
    <NumberField
      label={`${label} (${spec.low}–${spec.high})`}
      min={spec.low}
      max={spec.high}
      value={String(value)}
      blocked={blocked}
      onChange={(next) => onChange(Math.round(Number(next) || 0))}
    />
  )
}
