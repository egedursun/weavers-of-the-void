import { Sparkles } from 'lucide-react'
import { KeyValueList, Section, StatBar } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { type AdjustGroup, AdjustStats } from '@/features/pantheon/AdjustStats'
import {
  RELATION_SCALE,
  STAT_MIN,
  STAT_SCALE,
} from '@/features/pantheon/constants'
import { STATS, humanize } from '@/features/pantheon/labels'
import {
  FOREIGN_EFFECT_LABEL,
  type ForeignGodDetail,
  editForeignGod,
} from './api'

const STAT_KEYS = new Set<string>(STATS.map((stat) => stat.key))

function editBody(key: string, value: number) {
  if (STAT_KEYS.has(key)) return { stats: { [key]: value } }
  return key === 'stance' ? { stance: value } : { power: value }
}

function adjustGroups(god: ForeignGodDetail['god']): AdjustGroup[] {
  return [
    {
      title: 'Stats',
      fields: STATS.map((stat) => ({
        key: stat.key,
        label: stat.label,
        value: god[stat.key],
        min: STAT_MIN,
        max: STAT_SCALE,
      })),
    },
    {
      title: 'Standing',
      fields: [
        {
          key: 'power',
          label: 'Power',
          value: god.power,
          min: 0,
          max: STAT_SCALE,
        },
        {
          key: 'stance',
          label: 'Attitude to the pantheon',
          value: god.stance,
          min: -RELATION_SCALE,
          max: RELATION_SCALE,
        },
      ],
    },
  ]
}

export function ForeignGodProfile({ detail }: { detail: ForeignGodDetail }) {
  const god = detail.god
  const personality = god.personality
  const existence = god.existence_profile
  return (
    <>
      <Section title='Stats' level={3}>
        <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
          {STATS.map((stat) => (
            <StatBar
              key={stat.key}
              label={stat.label}
              icon={stat.icon}
              value={god[stat.key]}
              max={STAT_SCALE}
              tone='mythic'
              showMax={false}
            />
          ))}
        </div>
        <AdjustStats
          id={`foreign-god-${god.id}-stat`}
          groups={adjustGroups(god)}
          note='Every change goes into the ledger and can be undone.'
          run={({ key, value }) => editForeignGod(god.id, editBody(key, value))}
        />
      </Section>
      <Section title='Powers' level={3}>
        {detail.powers.length === 0 ? (
          <Muted>
            No power written yet; deepening gives powers, or add one yourself
            below.
          </Muted>
        ) : (
          <ul className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
            {detail.powers.map((power) => (
              <li
                key={power.slot}
                className='flex min-w-0 flex-col gap-1 rounded-lg border p-3'
              >
                <div className='flex min-w-0 items-center gap-2'>
                  <Sparkles
                    aria-hidden='true'
                    className='size-icon-sm shrink-0 text-primary'
                  />
                  <Text weight='semibold' truncate>
                    {power.name}
                  </Text>
                </div>
                <Label>
                  {FOREIGN_EFFECT_LABEL[
                    power.effect as keyof typeof FOREIGN_EFFECT_LABEL
                  ] ?? humanize(power.effect)}
                </Label>
                {power.description && (
                  <Muted variant='caption'>{power.description}</Muted>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>
      <Section title='Personality and existence' level={3}>
        {personality || existence ? (
          <KeyValueList
            items={[
              ...(personality
                ? [
                    {
                      label: 'Appearance',
                      value: personality.appearance || '—',
                    },
                    {
                      label: 'Temperament',
                      value: personality.temperament || '—',
                    },
                    { label: 'Obsession', value: personality.obsession || '—' },
                    { label: 'Fear', value: personality.fear || '—' },
                    { label: 'Speech', value: personality.speech_style || '—' },
                    { label: 'Secret', value: personality.secret || '—' },
                  ]
                : []),
              ...(existence
                ? [
                    { label: 'Nature', value: existence.nature || '—' },
                    {
                      label: 'State',
                      value: existence.mode ? humanize(existence.mode) : '—',
                    },
                    {
                      label: 'Manifestation',
                      value: existence.manifestation || '—',
                    },
                    { label: 'True name', value: existence.true_name || '—' },
                  ]
                : []),
            ]}
          />
        ) : (
          <Muted>
            Not written yet; deepening writes personality and existence.
          </Muted>
        )}
      </Section>
    </>
  )
}
