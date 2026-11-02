import { APP_NAME } from '@/config/brand'
import { Section } from '@/components/domain'
import {
  Label,
  Muted,
  PageTitle,
  SectionTitle,
  Stat,
  Text,
} from '@/components/typography'
import { Row, Specimen } from './Specimen'
import { LONG_NAME, LONG_SENTENCE } from './fixtures'

const FAMILIES = [
  {
    name: 'Cinzel Decorative',
    role: 'The wordmark only: the name of the studio.',
    className: 'font-brand',
  },
  {
    name: 'Cinzel',
    role: 'Titles and records: carved like the gold of the crest.',
    className: 'font-display',
  },
  {
    name: 'Nunito Sans',
    role: 'Everything you read and touch: soft curves, clear at any size.',
    className: 'font-nunito',
  },
] as const

export function TypographySpecimens() {
  return (
    <Section
      title='Typography'
      description='Three faces, each with one job; each text role has exactly one size.'
      level={3}
    >
      <Specimen name='Families'>
        <div className='grid min-w-0 grid-cols-1 gap-3 lg:grid-cols-3'>
          {FAMILIES.map((family) => (
            <div
              key={family.name}
              className='flex min-w-0 flex-col gap-2 rounded-xl border bg-card p-4'
            >
              <PageTitle className={family.className} truncate>
                {'Aa \u011e\u011f \u015e\u015f'}
              </PageTitle>
              <Text weight='semibold' className={family.className}>
                {family.name}
              </Text>
              <Muted variant='caption'>{family.role}</Muted>
            </div>
          ))}
        </div>
      </Specimen>
      <Specimen name='Wordmark'>
        <Text weight='semibold' className='font-brand text-primary'>
          {`${APP_NAME}®`}
        </Text>
      </Specimen>
      <Specimen name='Page title'>
        <PageTitle>The Pantheon of Orvael</PageTitle>
      </Specimen>
      <Specimen name='Section title'>
        <SectionTitle level={3}>Sons of the first age</SectionTitle>
      </Specimen>
      <Specimen name='Body'>
        <Text>{LONG_SENTENCE}</Text>
      </Specimen>
      <Specimen name='Prose'>
        <Text variant='prose'>{LONG_SENTENCE}</Text>
      </Specimen>
      <Specimen name='Caption'>
        <Text variant='caption'>Epoch 12, year 340 of the black sun</Text>
      </Specimen>
      <Specimen name='Muted'>
        <Muted>Secondary text explains without competing.</Muted>
      </Specimen>
      <Specimen name='Label'>
        <Row>
          <Label>Population</Label>
          <Label variant='overline'>Overline</Label>
        </Row>
      </Specimen>
      <Specimen name='Stat'>
        <Row>
          <Text>
            Essence <Stat value={12840} /> of <Stat value={20000} />
          </Text>
          <Stat value={0.42} format='percent' size='kpi' />
          <Stat value={1284000} format='compact' size='kpi' unit='mortals' />
        </Row>
      </Specimen>
      <Specimen name='Truncation'>
        <Text truncate>{LONG_NAME}</Text>
        <Text truncate={2}>
          {LONG_SENTENCE} {LONG_SENTENCE}
        </Text>
        <Text>{LONG_NAME}</Text>
      </Specimen>
    </Section>
  )
}
