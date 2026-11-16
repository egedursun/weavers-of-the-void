import { Cog } from 'lucide-react'
import { Switch } from '@/components/ui/switch'
import { RangeField } from '@/components/domain'
import { Medallion } from '@/components/domain/KpiTile'
import { SettingGroup } from '@/components/domain/SettingsKit'
import { Muted, Text } from '@/components/typography'
import { FAMILIES } from '@/features/technology/labels'
import { type TechFamily } from './api'
import { type StepProps } from './wizardTypes'

const FAMILY_KEYS = Object.keys(FAMILIES) as TechFamily[]

export function TechnologyFamilyFields({ draft, update, options }: StepProps) {
  const eraLevel = options.technology_levels[draft.technology] ?? 0
  const max = options.technology_level_max
  const set = Object.keys(draft.technologyLevels).length > 0
  const era = (
    options.technology[draft.technology] ?? draft.technology
  ).toLowerCase()
  const fill = (on: boolean) =>
    update({
      technologyLevels: on
        ? Object.fromEntries(FAMILY_KEYS.map((family) => [family, eraLevel]))
        : {},
    })
  return (
    <SettingGroup
      label='Technology by family'
      description='Each family of technique can stand at its own level; left unset, every family starts at the level of the chosen technology.'
    >
      <div className='flex min-w-0 flex-col gap-4 rounded-md border surface-well border-gild/20 bg-muted/60 p-4'>
        <div className='flex min-w-0 flex-wrap items-center gap-3'>
          <Medallion icon={Cog} tone='gold' size='sm' />
          <div className='flex min-w-0 flex-1 basis-48 flex-col gap-0.5'>
            <Text as='span' weight='semibold'>
              Set each family yourself
            </Text>
            <Muted variant='caption'>
              {set
                ? `Families you leave as they are stay at ${eraLevel} of ${max}.`
                : `Every family starts at ${eraLevel} of ${max}, the level of ${era}.`}
            </Muted>
          </div>
          <Switch
            aria-label='Set each family of technology yourself'
            checked={set}
            onCheckedChange={fill}
          />
        </div>
        {set && (
          <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
            {FAMILY_KEYS.map((family) => {
              const named = FAMILIES[family]
              const value = draft.technologyLevels[family] ?? eraLevel
              return (
                <RangeField
                  key={family}
                  label={named.label}
                  icon={named.icon}
                  value={value}
                  min={0}
                  max={max}
                  level={`${value} of ${max}`}
                  lowLabel='None'
                  highLabel='Highest'
                  onChange={(level) =>
                    update({
                      technologyLevels: {
                        ...draft.technologyLevels,
                        [family]: level,
                      },
                    })
                  }
                />
              )
            })}
          </div>
        )}
      </div>
    </SettingGroup>
  )
}
