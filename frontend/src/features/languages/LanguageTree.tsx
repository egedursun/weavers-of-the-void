import { useMemo } from 'react'
import {
  ArrowLeftRight,
  BookA,
  CaseSensitive,
  ExternalLink,
  GitBranch,
  GitFork,
  Users,
  WholeWord,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  Medallion,
  MiniStat,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted, SectionTitle, Text } from '@/components/typography'
import { FamilyChart } from './FamilyChart'
import {
  LanguageSeal,
  LetterTiles,
  Lineage,
  NameChips,
  ScriptBadge,
  SoundSignature,
} from './LanguageParts'
import { LanguageShaper } from './LanguageShaper'
import {
  type Family,
  type LanguageNode,
  buildFamilies,
  relativesOf,
} from './languageFamilies'
import { lineageOf } from './treeLayout'

type LanguageTreeProps = {
  nodes: LanguageNode[]
  covers: Map<number, string | null>
  selected: number | null
  onSelect: (id: number) => void
  onOpenDictionary: (id: number) => void
  readOnlyReason: string | null
}

function familySize(family: Family): number {
  return 1 + family.children.reduce((sum, child) => sum + familySize(child), 0)
}

function familyWords(family: Family): number {
  return (
    family.node.words +
    family.children.reduce((sum, child) => sum + familyWords(child), 0)
  )
}

function chainOf(nodes: LanguageNode[], self: LanguageNode): LanguageNode[] {
  const line = lineageOf(nodes, self.language.id)
  const byId = new Map(nodes.map((node) => [node.language.id, node]))
  const ordered: LanguageNode[] = []
  let current: LanguageNode | undefined = self
  while (
    current &&
    line.has(current.language.id) &&
    !ordered.includes(current)
  ) {
    ordered.unshift(current)
    const parentId: number | null = current.parent_language_id
    current = parentId === null ? undefined : byId.get(parentId)
  }
  return ordered
}

function IsolateCard({
  node,
  cover,
  active,
  onSelect,
}: {
  node: LanguageNode
  cover: string | null
  active: boolean
  onSelect: () => void
}) {
  return (
    <Button
      variant='outline'
      size='tile'
      aria-pressed={active}
      onClick={onSelect}
      className={cn(active && 'border-primary/50 bg-primary/10')}
    >
      <LanguageSeal
        name={node.language.name}
        size='sm'
        active={active}
        cover={cover}
      />
      <span className='flex min-w-0 flex-1 flex-col'>
        <Text as='span' weight='medium' truncate>
          {node.language.name}
        </Text>
        <Muted as='span' variant='caption' truncate>
          {`${formatInteger(node.words)} words · ${formatInteger(node.speakers)} speakers`}
        </Muted>
      </span>
    </Button>
  )
}

function CognateRow({
  cognate,
}: {
  cognate: LanguageNode['cognates'][number]
}) {
  return (
    <li className='flex min-w-0 items-center gap-2 rounded-lg border bg-background p-2'>
      <span className='flex min-w-0 flex-1 flex-col'>
        <Text as='span' weight='semibold' className='font-display' truncate>
          {cognate.first_word}
        </Text>
        <Muted as='span' variant='caption' truncate>
          {cognate.first_meaning}
        </Muted>
      </span>
      <ArrowLeftRight
        aria-hidden='true'
        className='size-icon-sm shrink-0 text-primary'
      />
      <span className='flex min-w-0 flex-1 flex-col items-end text-end'>
        <Text as='span' weight='semibold' className='font-display' truncate>
          {cognate.second_word}
        </Text>
        <Muted as='span' variant='caption' truncate>
          {cognate.second_meaning}
        </Muted>
      </span>
    </li>
  )
}

function LanguageDetail({
  nodes,
  covers,
  self,
  onSelect,
  onOpenDictionary,
}: {
  nodes: LanguageNode[]
  covers: Map<number, string | null>
  self: LanguageNode
  onSelect: (id: number) => void
  onOpenDictionary: (id: number) => void
}) {
  const { parent, daughters } = relativesOf(nodes, self.language.id)
  const chain = useMemo(() => chainOf(nodes, self), [nodes, self])
  return (
    <div className='flex min-w-0 flex-col gap-4 rounded-xl border bg-card p-4'>
      <div className='flex min-w-0 items-start gap-3'>
        <LanguageSeal
          name={self.language.name}
          size='lg'
          active
          cover={covers.get(self.language.id) ?? null}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
          <SectionTitle level={3} truncate={2}>
            {self.language.name}
          </SectionTitle>
          {self.language.subtype && (
            <Muted variant='caption'>{self.language.subtype}</Muted>
          )}
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <ScriptBadge script={self.writing_system} />
            <Badge size='sm' variant='outline'>
              {parent ? `Daughter of ${parent.language.name}` : 'A root tongue'}
            </Badge>
          </div>
        </div>
      </div>
      <Lineage chain={chain} onSelect={onSelect} />
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <MiniStat
          icon={WholeWord}
          label='Words'
          value={self.words}
          tone='gold'
        />
        <MiniStat
          icon={Users}
          label='Speakers'
          value={self.speakers}
          tone='verdigris'
        />
        <MiniStat
          icon={CaseSensitive}
          label='Letters'
          value={self.alphabet.length}
          tone='info'
        />
        <MiniStat
          icon={GitFork}
          label='Daughters'
          value={daughters.length}
          tone='muted'
        />
      </div>
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Sound signature</Label>
        <SoundSignature signature={self.signature} />
      </div>
      {self.alphabet.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Alphabet</Label>
          <LetterTiles letters={self.alphabet} label='Alphabet' />
        </div>
      )}
      {self.sample_names.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Names in this tongue</Label>
          <NameChips names={self.sample_names} />
        </div>
      )}
      {daughters.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Daughter tongues</Label>
          <PagedList
            items={daughters}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap gap-1.5'
            itemKey={(daughter) => daughter.language.id}
          >
            {(daughter) => (
              <Button
                key={daughter.language.id}
                size='sm'
                variant='outline'
                onClick={() => onSelect(daughter.language.id)}
              >
                <GitBranch />
                {daughter.language.name}
              </Button>
            )}
          </PagedList>
        </div>
      )}
      {self.cognates.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>
            {parent
              ? `Shared roots with ${parent.language.name}`
              : 'Shared roots'}
          </Label>
          <ul className='flex min-w-0 flex-col gap-1.5'>
            {self.cognates.map((cognate, index) => (
              <CognateRow key={index} cognate={cognate} />
            ))}
          </ul>
        </div>
      )}
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button size='sm' onClick={() => onOpenDictionary(self.language.id)}>
          <BookA />
          Open its dictionary
        </Button>
        <EntityLink kind='entity' id={String(self.language.id)}>
          <ExternalLink aria-hidden='true' className='size-icon-sm' />
          Its page
        </EntityLink>
      </div>
    </div>
  )
}

export function LanguageTree({
  nodes,
  covers,
  selected,
  onSelect,
  onOpenDictionary,
  readOnlyReason,
}: LanguageTreeProps) {
  const { families, loners } = useMemo(() => buildFamilies(nodes), [nodes])
  const ordered = useMemo(
    () =>
      [...families].sort((left, right) => familySize(right) - familySize(left)),
    [families]
  )
  const chosen =
    selected !== null && nodes.some((node) => node.language.id === selected)
      ? selected
      : (ordered[0]?.node.language.id ?? nodes[0]?.language.id ?? null)
  const lineage = useMemo(
    () => (chosen === null ? new Set<number>() : lineageOf(nodes, chosen)),
    [nodes, chosen]
  )
  if (nodes.length === 0 || chosen === null)
    return (
      <EmptyState
        icon={GitBranch}
        title='No languages yet'
        description='Language families grow as peoples split and wander.'
      />
    )
  const self = nodes.find((node) => node.language.id === chosen)
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <div className='grid min-w-0 grid-cols-1 gap-6 xl:grid-cols-3'>
        <div className='flex min-w-0 flex-col gap-6 xl:col-span-2'>
          {ordered.length > 0 && (
            <Section
              id='languages-families'
              title='Families'
              description='Each tongue gave birth to the ones on its right. The lit line is the lineage of the chosen language.'
              level={3}
            >
              <ul className='flex min-w-0 flex-col gap-4'>
                {ordered.map((family) => (
                  <li
                    key={family.node.language.id}
                    className='flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-4'
                  >
                    <div className='flex min-w-0 flex-wrap items-center gap-3'>
                      <Medallion icon={GitBranch} tone='verdigris' size='sm' />
                      <Text
                        as='span'
                        weight='semibold'
                        truncate
                        className='min-w-0 flex-1'
                      >
                        {`The ${family.node.language.name} family`}
                      </Text>
                      <Badge size='sm' variant='outline'>
                        {`${familySize(family)} tongues`}
                      </Badge>
                      <Badge size='sm' variant='outline'>
                        {`${formatInteger(familyWords(family))} words`}
                      </Badge>
                    </div>
                    <FamilyChart
                      family={family}
                      covers={covers}
                      selected={chosen}
                      lineage={lineage}
                      onSelect={onSelect}
                    />
                  </li>
                ))}
              </ul>
            </Section>
          )}
          {loners.length > 0 && (
            <Section
              id='languages-loners'
              title='Isolates'
              description='Tongues with no known mother and no daughters yet.'
              level={3}
            >
              <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 2xl:grid-cols-3'>
                {loners.map((node) => (
                  <li key={node.language.id} className='min-w-0'>
                    <IsolateCard
                      node={node}
                      cover={covers.get(node.language.id) ?? null}
                      active={chosen === node.language.id}
                      onSelect={() => onSelect(node.language.id)}
                    />
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>
        {self && (
          <div className='min-w-0 xl:sticky xl:top-topbar xl:self-start'>
            <LanguageDetail
              nodes={nodes}
              covers={covers}
              self={self}
              onSelect={onSelect}
              onOpenDictionary={onOpenDictionary}
            />
          </div>
        )}
      </div>
      {self && (
        <LanguageShaper
          key={self.language.id}
          node={self}
          readOnlyReason={readOnlyReason}
        />
      )}
    </div>
  )
}
