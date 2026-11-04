import {
  HeartPulse,
  Shield,
  Skull,
  Swords,
  type LucideIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { type KpiTone, Medallion } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { type Rule, rulePath, useRules, useSaveRules } from './api'

const PROFILE_PATH = 'harshness.profile'
const PROFILES: {
  value: number
  key: string
  label: string
  icon: LucideIcon
  tone: KpiTone
  hint: string
}[] = [
  {
    value: 0,
    key: 'heroic',
    label: 'Heroic',
    icon: Shield,
    tone: 'success',
    hint: 'Heroes shrug off wounds; plague and famine spare more.',
  },
  {
    value: 1,
    key: 'realistic',
    label: 'Realistic',
    icon: Swords,
    tone: 'gold',
    hint: 'Rates near history: a famous king can die of one arrow.',
  },
  {
    value: 2,
    key: 'brutal',
    label: 'Brutal',
    icon: Skull,
    tone: 'danger',
    hint: 'Wounds fester, lasting harm is common, losses are heavy.',
  },
]
const SCALES: { key: string; label: string }[] = [
  { key: 'wound_lethality', label: 'Wound lethality' },
  { key: 'infection', label: 'Festering' },
  { key: 'permanent_injury', label: 'Lasting harm' },
  { key: 'disease_death', label: 'Disease deaths' },
  { key: 'famine_death', label: 'Famine deaths' },
  { key: 'childbirth_death', label: 'Childbirth deaths' },
  { key: 'battle_loss', label: 'Battle losses' },
  { key: 'notable_survival', label: 'Notables spared' },
]

export function HarshnessDial() {
  const rules = useRules()
  const save = useSaveRules()
  const byPath = new Map<string, Rule>(
    (rules.data ?? []).map((rule) => [rulePath(rule), rule])
  )
  const profile = byPath.get(PROFILE_PATH)
  if (!profile) return null
  const current = PROFILES.find((item) => item.value === profile.value)
  const choose = (value: number) => {
    if (value === profile.value) return
    save.mutate(new Map([[profile, value]]), {
      onSuccess: () =>
        toast.success(
          `The world is now ${PROFILES[value]?.label.toLowerCase()}.`
        ),
      onError: (error) => toast.error(error.message),
    })
  }
  return (
    <div
      data-surface='HarshnessDial'
      className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={HeartPulse} tone={current?.tone ?? 'gold'} size='sm' />
        <div className='flex min-w-0 flex-col'>
          <Label variant='overline'>Harshness</Label>
          <Muted variant='caption'>
            One dial scales every lethality and loss together. Single rules
            below can still be set by hand.
          </Muted>
        </div>
      </div>
      <div
        role='radiogroup'
        aria-label='Harshness of the world'
        className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'
      >
        {PROFILES.map((item) => {
          const chosen = item.value === profile.value
          return (
            <Button
              key={item.key}
              type='button'
              role='radio'
              aria-checked={chosen}
              variant={chosen ? 'secondary' : 'outline'}
              disabled={save.isPending}
              disabledReason={save.isPending ? 'Working on it.' : undefined}
              onClick={() => choose(item.value)}
            >
              <item.icon />
              {item.label}
            </Button>
          )
        })}
      </div>
      {current && (
        <div className='flex min-w-0 items-center gap-2'>
          <Medallion icon={current.icon} tone={current.tone} size='sm' />
          <Text>{current.hint}</Text>
        </div>
      )}
      {current && (
        <ul className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4'>
          {SCALES.map((scale) => {
            const rule = byPath.get(`harshness.${current.key}_${scale.key}_pct`)
            return (
              <li
                key={scale.key}
                className='flex min-w-0 flex-col rounded-md border px-2 py-1'
              >
                <Muted variant='caption' truncate>
                  {scale.label}
                </Muted>
                <Text weight='semibold'>{`${rule?.value ?? 100}%`}</Text>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
