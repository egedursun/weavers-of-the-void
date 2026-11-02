import { useState } from 'react'
import {
  CloudLightning,
  Crown,
  Flame,
  HandHeart,
  Shield,
  Sparkles,
  Swords,
} from 'lucide-react'
import { RARITIES } from '@/constants/rarity'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  EpochSlider,
  JobProgress,
  KeyValueList,
  PageHeader,
  Portrait,
  type PortraitSize,
  RarityBadge,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
  CodeBlock,
  CopyButton,
  DomainGlyph,
  RuleInfo,
  Sigil,
  ChronicleKindIcon,
  DomainIcon,
  ToolIcon,
} from '@/components/domain'
import { FilePicker } from '@/components/domain/FilePicker'
import { LineChart } from '@/components/domain/LineChart'
import { MentionText } from '@/components/domain/MentionText'
import { MultiSelect } from '@/components/domain/MultiSelect'
import { RecordNavLink } from '@/components/domain/RecordNavLink'
import { CHRONICLE_KIND_ICON } from '@/components/domain/chronicleKindIcons'
import {
  ICON_VOCABULARIES,
  type IconVocabulary,
} from '@/components/domain/domainIcons'
import { TOOL_ICON } from '@/components/domain/toolIcons'
import { Muted, Text } from '@/components/typography'
import { Row, Specimen } from './Specimen'
import { BROKEN_IMAGE, LONG_NAME } from './fixtures'

const PORTRAIT_SIZES: PortraitSize[] = ['xs', 'sm', 'md', 'lg', 'xl']

export function DomainSpecimens() {
  return (
    <Section
      title='Domain'
      description='Shared building blocks of every screen.'
      level={3}
    >
      <Specimen name='Rarity badge'>
        <Row>
          {RARITIES.map((rarity) => (
            <RarityBadge key={rarity} rarity={rarity} />
          ))}
        </Row>
        <Row>
          {RARITIES.map((rarity) => (
            <RarityBadge
              key={rarity}
              rarity={rarity}
              size='sm'
              showIcon={false}
            />
          ))}
        </Row>
      </Specimen>
      <Specimen name='Entity link'>
        <Text>
          <EntityLink kind='son' id='7' rarity='legendary' showIcon>
            Ithren the Unbowed
          </EntityLink>{' '}
          raised{' '}
          <EntityLink kind='entity' id='42'>
            the Salt Crown
          </EntityLink>{' '}
          against{' '}
          <EntityLink kind='foreign-god' id='3' showIcon>
            the Hollow Star
          </EntityLink>
          .
        </Text>
        <Text>
          <EntityLink kind='entity' id='99'>
            {LONG_NAME}
          </EntityLink>
        </Text>
      </Specimen>
      <Specimen name='Rule info, copy button, sigil and domain glyph'>
        <Row>
          <RuleInfo rule='costs.summon_son' label='The summon cost' />
          <CopyButton
            text='A pale star only the dying can see'
            label='Copy the sample'
          />
          {RARITIES.map((rarity) => (
            <span
              key={rarity}
              className='inline-flex size-portrait-md items-center justify-center'
            >
              <Sigil seed={LONG_NAME} rarity={rarity} />
            </span>
          ))}
          <DomainGlyph domain='sea' />
        </Row>
      </Specimen>
      <Specimen name='Icon vocabulary'>
        {(Object.keys(ICON_VOCABULARIES) as IconVocabulary[]).map(
          (vocabulary) => (
            <Row key={vocabulary}>
              <Muted variant='caption'>{vocabulary}</Muted>
              {Object.keys(ICON_VOCABULARIES[vocabulary]).map((value) => (
                <DomainIcon key={value} vocabulary={vocabulary} value={value} />
              ))}
            </Row>
          )
        )}
        <Row>
          <Muted variant='caption'>chronicle kind</Muted>
          {Object.keys(CHRONICLE_KIND_ICON).map((kind) => (
            <ChronicleKindIcon key={kind} kind={kind} />
          ))}
        </Row>
        <Row>
          <Muted variant='caption'>tool</Muted>
          {Object.keys(TOOL_ICON).map((tool) => (
            <ToolIcon key={tool} tool={tool} />
          ))}
        </Row>
      </Specimen>
      <Specimen name='Code block'>
        <CodeBlock
          label='Output schema'
          meta='3 fields'
          text={JSON.stringify(
            {
              type: 'object',
              properties: {
                verdict: { enum: ['accepted', 'rejected', 'limbo'] },
                rationale: { type: 'string' },
                motifs: { type: 'array', items: { type: 'string' } },
              },
            },
            null,
            2
          )}
        />
        <CodeBlock
          label='Rendered block'
          text=''
          empty='This block is empty.'
        />
      </Specimen>
      <Specimen name='Stat bar'>
        <div className='grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2'>
          <StatBar label='Strength' value={14} max={20} icon={Swords} />
          <StatBar
            label='Endurance'
            value={8}
            max={20}
            icon={Shield}
            tone='success'
          />
          <StatBar
            label='Wrath'
            value={17}
            max={20}
            icon={Flame}
            tone='destructive'
          />
          <StatBar label={LONG_NAME} value={3} max={20} tone='mythic' />
        </div>
      </Specimen>
      <Specimen name='Portrait'>
        <Row>
          {PORTRAIT_SIZES.map((size) => (
            <Portrait key={size} name='Ithren Unbowed' size={size} />
          ))}
        </Row>
        <Row>
          {RARITIES.map((rarity) => (
            <Portrait key={rarity} name={rarity} size='md' rarity={rarity} />
          ))}
          <Portrait
            name='Broken image'
            src={BROKEN_IMAGE}
            size='md'
            shape='square'
          />
        </Row>
      </Specimen>
      <Specimen name='Key value list'>
        <KeyValueList
          items={[
            { label: 'Epoch', value: '12' },
            { label: 'Star of the epoch', value: 'The Black Sun' },
            { label: 'Doom clock', value: '7 of 12' },
            { label: LONG_NAME, value: LONG_NAME },
          ]}
        />
      </Specimen>
      <Specimen name='Timeline'>
        <Timeline label='Recent history'>
          <TimelineItem
            icon={Crown}
            title='Ithren ascended to legendary'
            timestamp='Epoch 12'
            tone='primary'
          >
            <Muted>The brothers watched in silence.</Muted>
          </TimelineItem>
          <TimelineItem
            icon={CloudLightning}
            title='A storm broke the northern fleet'
            timestamp='Epoch 11'
            tone='destructive'
          />
          <TimelineItem
            icon={HandHeart}
            title={LONG_NAME}
            timestamp='Epoch 10'
            tone='success'
            last
          />
        </Timeline>
      </Specimen>
      <Specimen name='Job progress'>
        <JobProgress
          job={{
            kind: 'epoch',
            status: 'running',
            progress: 0.42,
            stage: 'Sons are acting',
            error: null,
          }}
        />
        <JobProgress
          job={{
            kind: 'image',
            status: 'queued',
            progress: 0,
            stage: null,
            error: null,
          }}
        />
        <JobProgress
          job={{
            kind: 'genesis',
            status: 'succeeded',
            progress: 1,
            stage: 'Done',
            error: null,
          }}
        />
        <JobProgress
          job={{
            kind: 'backup',
            status: 'failed',
            progress: 0.6,
            stage: null,
            error: 'The disk is full.',
          }}
          action={
            <Button size='sm' variant='outline'>
              Retry
            </Button>
          }
        />
      </Specimen>
      <Specimen name='Empty state'>
        <EmptyState
          icon={Sparkles}
          title='No prayers yet'
          description='They appear here when your sons or mortals wish for something.'
          action={<Button size='sm'>Write a revelation</Button>}
        />
      </Specimen>
      <Specimen name='Page header'>
        <PageHeader
          eyebrow='Son'
          title={LONG_NAME}
          description='A page header keeps its actions in the flow, never on top of the title.'
          icon={Crown}
          meta={<RarityBadge rarity='mythic' />}
          actions={
            <>
              <Button variant='outline'>Edit</Button>
              <Button>Command</Button>
            </>
          }
        />
      </Specimen>
      <Specimen name='Epoch slider'>
        <EpochSliderSpecimen />
      </Specimen>
      <Specimen name='Line chart'>
        <LineChart title='Population and disciples' series={CHART_SERIES} />
        <LineChart
          title='Existence'
          series={[CHART_SERIES[1]]}
          max={CHART_MAX}
        />
      </Specimen>
      <Specimen name='Multi-select'>
        <MultiSelectSpecimen />
      </Specimen>
      <Specimen name='File picker'>
        <FilePickerSpecimen />
      </Specimen>
      <Specimen name='Record jump links'>
        <Row>
          <RecordNavLink to={{ view: 'map', world: 1, focus: 2 }} />
          <RecordNavLink to={{ view: 'network', focus: 2 }} />
          <RecordNavLink to={{ view: 'chronicle', epoch: 3 }} />
          <RecordNavLink to={{ view: 'climate', world: 1 }} />
          <RecordNavLink to={{ view: 'atlas', type: 'people' }}>
            Peoples in the atlas
          </RecordNavLink>
        </Row>
      </Specimen>
      <Specimen name='Mention text'>
        <Text>
          <MentionText text='A story without tokens stays plain text; route#4 reads as a road.' />
        </Text>
      </Specimen>
    </Section>
  )
}

const CHART_MAX = 100
const CHART_SERIES = [
  {
    key: 'population',
    label: 'Population',
    color: 'var(--chart-1)',
    points: [1, 2, 3, 4, 5, 6].map((x) => ({ x, y: 20 + x * 11 })),
  },
  {
    key: 'disciples',
    label: 'Disciples',
    color: 'var(--chart-2)',
    points: [1, 2, 3, 4, 5, 6].map((x) => ({ x, y: 8 + x * 6 })),
  },
]

function MultiSelectSpecimen() {
  const [value, setValue] = useState<string[]>(['war'])
  return (
    <MultiSelect
      label='Kinds'
      min={2}
      options={[
        { value: 'war', label: 'War' },
        { value: 'birth', label: 'Birth' },
        { value: 'death', label: 'Death', detail: LONG_NAME },
      ]}
      value={value}
      onChange={setValue}
    />
  )
}

function FilePickerSpecimen() {
  const [file, setFile] = useState<File | null>(null)
  return (
    <FilePicker
      file={file}
      onChange={setFile}
      accept='.aerona'
      label='Drop a .aerona package here'
      hint='Exported from Weavers of the Void with or without its images.'
    />
  )
}

function EpochSliderSpecimen() {
  const [epoch, setEpoch] = useState(7)
  return <EpochSlider label='Time' value={epoch} max={12} onChange={setEpoch} />
}
