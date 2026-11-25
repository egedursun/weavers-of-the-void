import { useState } from 'react'
import {
  Clock,
  Footprints,
  Hourglass,
  Layers,
  MemoryStick,
  RotateCcw,
  Save,
  SlidersHorizontal,
  TriangleAlert,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatDecimal } from '@/lib/format'
import { plural } from '@/lib/units'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { RangeField, Section } from '@/components/domain'
import {
  ChoiceTiles,
  SettingGroup,
  SettingRow,
} from '@/components/domain/SettingsKit'
import { Muted, Text } from '@/components/typography'
import { toastDone } from '@/features/team/outcome'
import {
  type Rule,
  useResetGroup,
  useRules,
  useSaveRules,
} from '@/features/world-rules/api'
import {
  ASPECTS,
  type AspectKey,
  RESOLUTIONS,
  type ResolutionKey,
  dimensionsOf,
  matchPreset,
  stepLevel,
} from './imageGenPresets'

const NAMESPACE = 'image_gen'
const SECONDS_PER_MINUTE = 60
const IDLE_CHOICES = [0, 300, 600, 1800, 3600] as const
const TIMEOUT_CHOICES = [120, 300, 600, 1200, 1800] as const
const RETRY_CHOICES = [0, 1, 2, 3] as const
const SLOW_PIXELS = 1440 * 1440
const SLOW_TIMEOUT_SECONDS = 1200

type Draft = Record<string, number>

function minutes(seconds: number): string {
  if (seconds === 0) return 'Never'
  return `${seconds / SECONDS_PER_MINUTE} min`
}

function ChoiceRow({
  label,
  value,
  choices,
  format,
  onChange,
}: {
  label: string
  value: number
  choices: readonly number[]
  format: (value: number) => string
  onChange: (value: number) => void
}) {
  const options = choices.includes(value)
    ? choices
    : [...choices, value].sort((left, right) => left - right)
  return (
    <ToggleGroup
      type='single'
      size='sm'
      variant='outline'
      value={String(value)}
      onValueChange={(next) => next && onChange(Number(next))}
      aria-label={label}
      className='w-full'
    >
      {options.map((choice) => (
        <ToggleGroupItem key={choice} value={String(choice)} className='grow'>
          {format(choice)}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  )
}

export function ImageGenSettings() {
  const rules = useRules()
  const save = useSaveRules()
  const reset = useResetGroup()
  const [draft, setDraft] = useState<Draft>({})
  const all = (rules.data ?? []).filter((rule) => rule.namespace === NAMESPACE)
  const byKey = new Map(all.map((rule) => [rule.key, rule]))
  const value = (key: string): number =>
    draft[key] ?? byKey.get(key)?.value ?? 0
  const fallback = (key: string): number => byKey.get(key)?.default ?? 0
  const set = (changes: Draft) => setDraft({ ...draft, ...changes })
  if (rules.isPending) return <Skeleton className='h-160 w-full' />
  if (rules.isError)
    return <Text tone='destructive'>{rules.error.message}</Text>

  const width = value('width')
  const height = value('height')
  const steps = value('steps')
  const preset = matchPreset(width, height)
  const resolution = preset?.resolution.value
  const aspect = preset?.aspect.value ?? 'square'
  const pickSize = (nextResolution: ResolutionKey, nextAspect: AspectKey) => {
    const chosenResolution = RESOLUTIONS.find(
      (item) => item.value === nextResolution
    )
    const chosenAspect = ASPECTS.find((item) => item.value === nextAspect)
    if (!chosenResolution || !chosenAspect) return
    set(dimensionsOf(chosenResolution, chosenAspect))
  }
  const cost =
    (width * height * steps) /
    Math.max(1, fallback('width') * fallback('height') * fallback('steps'))
  const changed = [...Object.entries(draft)].filter(
    ([key, next]) => byKey.get(key)?.value !== next
  )
  const customized = all.filter((rule) => rule.value !== rule.default)
  const slow =
    width * height >= SLOW_PIXELS &&
    value('image_timeout_seconds') < SLOW_TIMEOUT_SECONDS
  const persist = () => {
    const changes = new Map<Rule, number>()
    for (const [key, next] of changed) {
      const rule = byKey.get(key)
      if (rule) changes.set(rule, next)
    }
    save.mutate(changes, {
      onSuccess: (result) => {
        setDraft({})
        toastDone(result, 'Image settings saved')
      },
      onError: (error) => toast.error(error.message),
    })
  }
  return (
    <Section
      title='Image generation'
      description='How every new image is painted. Saved with the world rules; the defaults are the studio defaults.'
      surface='card'
      level={3}
      icon={SlidersHorizontal}
      actions={
        <>
          <Button
            act={reset}
            variant='outline'
            size='sm'
            disabled={customized.length === 0 || reset.isPending}
            disabledReason='Everything is already at its default'
            onClick={() =>
              reset.mutate(customized, {
                onSuccess: (result) => {
                  setDraft({})
                  toastDone(result, 'Image settings back to their defaults')
                },
                onError: (error) => toast.error(error.message),
              })
            }
          >
            <RotateCcw />
            Defaults
          </Button>
          <Button
            act={save}
            size='sm'
            disabled={changed.length === 0 || save.isPending}
            disabledReason='Nothing has changed'
            onClick={persist}
          >
            <Save />
            {changed.length > 0 ? `Save ${changed.length}` : 'Saved'}
          </Button>
        </>
      }
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Badge variant='outline'>{`${width} × ${height} px`}</Badge>
        <Badge variant='outline'>{`${plural(steps, 'step', 'steps')}`}</Badge>
        <Badge variant={cost > 1 ? 'warning' : 'success'}>
          {cost === 1
            ? 'Default speed'
            : `About ${formatDecimal(cost, 1)}× the default time per image`}
        </Badge>
        {!preset && <Badge variant='secondary'>Custom size</Badge>}
      </div>
      <SettingGroup
        label='Resolution'
        description='The short side of every image. Larger images take much longer and need more memory.'
      >
        <ChoiceTiles
          label='Resolution'
          value={resolution ?? ('' as ResolutionKey)}
          options={RESOLUTIONS}
          onChange={(next) => pickSize(next, aspect)}
          columns={3}
        />
      </SettingGroup>
      <SettingGroup
        label='Shape'
        description='The frame of every image; square suits portraits and covers.'
      >
        <ChoiceTiles
          label='Shape'
          value={aspect}
          options={ASPECTS}
          onChange={(next) =>
            pickSize(resolution ?? RESOLUTIONS[1].value, next)
          }
          columns={3}
        />
      </SettingGroup>
      <RangeField
        label='Steps'
        icon={Footprints}
        hint='Denoising steps per image: few are fast, many add detail'
        value={steps}
        min={1}
        max={50}
        level={stepLevel(steps)}
        lowLabel='1 · fastest'
        highLabel='50 · slowest'
        onChange={(next) => set({ steps: next })}
      />
      <SettingRow
        icon={Layers}
        label='Paint new records after every epoch'
        description='At the end of an epoch, start painting every record that has no image yet.'
        active={value('auto') === 1}
      >
        {(id) => (
          <Switch
            id={id}
            checked={value('auto') === 1}
            onCheckedChange={(checked) => set({ auto: checked ? 1 : 0 })}
          />
        )}
      </SettingRow>
      <div className='grid min-w-0 grid-cols-1 gap-4 lg:grid-cols-3'>
        <SettingGroup
          label='Retries'
          description='Tries again when an image fails in a batch.'
        >
          <ChoiceRow
            label='Retries'
            value={value('retries')}
            choices={RETRY_CHOICES}
            format={(choice) => (choice === 0 ? 'None' : `${choice}×`)}
            onChange={(next) => set({ retries: next })}
          />
        </SettingGroup>
        <SettingGroup
          label='Keep the model loaded'
          description='How long an idle worker holds the model in memory.'
        >
          <ChoiceRow
            label='Keep the model loaded'
            value={value('idle_unload_seconds')}
            choices={IDLE_CHOICES}
            format={(choice) => (choice === 0 ? 'Always' : minutes(choice))}
            onChange={(next) => set({ idle_unload_seconds: next })}
          />
        </SettingGroup>
        <SettingGroup
          label='Time limit per image'
          description='A single image that takes longer is stopped and the worker restarts.'
        >
          <ChoiceRow
            label='Time limit per image'
            value={value('image_timeout_seconds')}
            choices={TIMEOUT_CHOICES}
            format={minutes}
            onChange={(next) => set({ image_timeout_seconds: next })}
          />
        </SettingGroup>
      </div>
      {slow && (
        <Alert>
          <TriangleAlert />
          <AlertTitle>Large images need more time</AlertTitle>
          <AlertDescription>
            {`At ${width} × ${height} one image can take many minutes. Raise the time limit per image to 20 or 30 minutes so the worker is not stopped midway.`}
          </AlertDescription>
        </Alert>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1'>
        <Muted variant='caption'>
          <Clock className='inline size-icon-xs' aria-hidden='true' />{' '}
          {`Model load wait: ${minutes(value('startup_timeout_seconds'))}`}
        </Muted>
        <Muted variant='caption'>
          <MemoryStick className='inline size-icon-xs' aria-hidden='true' />{' '}
          {`Log keeps ${value('log_lines')} lines`}
        </Muted>
        <Muted variant='caption'>
          <Hourglass className='inline size-icon-xs' aria-hidden='true' /> Every
          value is also in World rules, Image generation.
        </Muted>
      </div>
    </Section>
  )
}
