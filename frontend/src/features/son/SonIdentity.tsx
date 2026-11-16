import { KeyValueList, Section } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { type SonRecord } from '@/features/pantheon/api'
import { humanize } from '@/features/pantheon/labels'

function Secret({ title, text }: { title: string; text: string }) {
  if (!text) return null
  return (
    <div className='flex min-w-0 flex-col gap-1 rounded-md p-3 sealed-well'>
      <Label variant='overline'>{title}</Label>
      <Muted>{text}</Muted>
    </div>
  )
}

export function SonIdentity({ son }: { son: SonRecord }) {
  const existence = son.existence_profile
  const personality = son.personality
  return (
    <>
      <Section title='Existence' level={3}>
        {existence ? (
          <>
            <KeyValueList
              items={[
                { label: 'Essence nature', value: existence.nature || '—' },
                {
                  label: 'State',
                  value: existence.mode ? humanize(existence.mode) : '—',
                },
                {
                  label: 'Manifestation',
                  value: existence.manifestation || '—',
                },
              ]}
            />
            <Secret
              title='True name (only you know)'
              text={existence.true_name}
            />
          </>
        ) : (
          <Muted>Their existence is not written yet.</Muted>
        )}
      </Section>
      <Section title='Who they are' level={3}>
        <KeyValueList
          items={[
            { label: 'Appearance', value: personality.appearance || '—' },
            { label: 'Temperament', value: personality.temperament || '—' },
            { label: 'Obsession', value: personality.obsession || '—' },
            { label: 'Fear', value: personality.fear || '—' },
            { label: 'Speech', value: personality.speech_style || '—' },
          ]}
        />
        <Secret title='Their secret' text={personality.secret} />
      </Section>
    </>
  )
}
