import { useMemo, useState } from 'react'
import {
  BookA,
  CaseSensitive,
  CalendarDays,
  ExternalLink,
  GitFork,
  Quote,
  Search,
  Users,
  WholeWord,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  EntityLink,
  MiniStat,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted, SectionTitle, Text } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Highlight } from '@/features/atlas/Highlight'
import { why } from '@/features/dominion/model'
import { humanize } from '@/features/entity/actions/schema'
import { useWorldState } from '@/features/entity/api/queries'
import { type LanguageView } from '@/features/entity/api/types'
import { MindPicker } from '@/features/entity/mind/parts'
import { useTongueAction } from '@/features/tongues/api'
import { REGISTERS } from '@/features/tongues/labels'
import { AddWordsForm } from './AddWordsForm'
import {
  LanguageSeal,
  LetterTiles,
  NameChips,
  ScriptBadge,
  SoundSignature,
} from './LanguageParts'
import { TranslationBox } from './TranslationBox'
import { type LanguageNode, relativesOf } from './languageFamilies'
import {
  PART_ICON,
  type PartOfSpeech,
  SCRIPT_ICON,
  UNWRITTEN_ICON,
} from './languageIcons'

const WORD_STEP = 48
const MATCH_LIMIT = 60
const ALL_PARTS = 'all'

type Lexeme = LanguageView['words'][number]

type DictionaryProps = {
  languages: LanguageView[]
  nodes: LanguageNode[]
  selected: number | null
  onSelect: (id: number) => void
  query: string
  onQuery: (query: string) => void
}

function RailItem({
  language,
  node,
  active,
  onSelect,
}: {
  language: LanguageView
  node: LanguageNode | undefined
  active: boolean
  onSelect: () => void
}) {
  const script = node?.writing_system ?? null
  const Script = script ? SCRIPT_ICON[script] : UNWRITTEN_ICON
  return (
    <Button
      variant='ghost'
      size='tile'
      aria-current={active ? 'true' : undefined}
      onClick={onSelect}
      className={cn(active && 'border-primary/50 bg-primary/10')}
    >
      <LanguageSeal
        name={language.language.name}
        size='sm'
        active={active}
        cover={language.cover}
      />
      <span className='flex min-w-0 flex-1 flex-col'>
        <Text as='span' weight='medium' truncate>
          {language.language.name}
        </Text>
        <Muted as='span' variant='caption' truncate>
          {language.language.subtype ??
            (node?.writing_system
              ? humanize(node.writing_system)
              : 'Spoken only')}
        </Muted>
      </span>
      <span className='flex shrink-0 flex-col items-end gap-0.5'>
        <Badge size='sm' variant={active ? 'default' : 'outline'}>
          {formatInteger(language.word_total)}
        </Badge>
        <Script
          aria-hidden='true'
          className='size-icon-xs text-muted-foreground'
        />
      </span>
    </Button>
  )
}

function LanguageRail({
  languages,
  nodes,
  current,
  onSelect,
}: {
  languages: LanguageView[]
  nodes: LanguageNode[]
  current: number
  onSelect: (id: number) => void
}) {
  const state = useWorldState()
  const [filter, setFilter] = useState('')
  const worlds = new Map(
    (state.data?.worlds ?? []).map((world) => [world.id, world.name])
  )
  const needle = filter.trim().toLowerCase()
  const shown = languages.filter(
    (language) =>
      !needle || language.language.name.toLowerCase().includes(needle)
  )
  const groups = new Map<number, LanguageView[]>()
  for (const language of shown)
    groups.set(language.language.world_id, [
      ...(groups.get(language.language.world_id) ?? []),
      language,
    ])
  const byNode = new Map(nodes.map((node) => [node.language.id, node]))
  return (
    <nav
      aria-label='Languages'
      className='flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-3'
    >
      <Input
        type='search'
        leadingIcon={Search}
        placeholder='Find a tongue'
        aria-label='Find a tongue'
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
      />
      <div className='flex max-h-200 min-w-0 flex-col gap-3 overflow-y-auto'>
        {[...groups.entries()].map(([worldId, items]) => (
          <div key={worldId} className='flex min-w-0 flex-col gap-1'>
            {worlds.size > 1 && (
              <Label variant='overline'>
                {`${worlds.get(worldId) ?? 'Unknown world'} · ${items.length}`}
              </Label>
            )}
            {[...items]
              .sort((left, right) => right.word_total - left.word_total)
              .map((language) => (
                <RailItem
                  key={language.language.id}
                  language={language}
                  node={byNode.get(language.language.id)}
                  active={language.language.id === current}
                  onSelect={() => onSelect(language.language.id)}
                />
              ))}
          </div>
        ))}
        {shown.length === 0 && (
          <Muted variant='caption'>No tongue goes by that name.</Muted>
        )}
      </div>
    </nav>
  )
}

function LanguageHero({
  current,
  node,
  nodes,
}: {
  current: LanguageView
  node: LanguageNode | undefined
  nodes: LanguageNode[]
}) {
  const { parent, daughters } = relativesOf(nodes, current.language.id)
  return (
    <div className='flex min-w-0 flex-col gap-4 rounded-xl border bg-card p-4'>
      <div className='flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start'>
        <LanguageSeal
          name={current.language.name}
          size='xl'
          active
          cover={current.cover}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-2'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <SectionTitle level={2} truncate={2} className='min-w-0 flex-1'>
              {current.language.name}
            </SectionTitle>
            <EntityLink kind='entity' id={String(current.language.id)}>
              <ExternalLink aria-hidden='true' className='size-icon-sm' />
              Its page
            </EntityLink>
          </div>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <ScriptBadge script={node?.writing_system ?? null} />
            {current.language.subtype && (
              <Badge size='sm' variant='outline'>
                {current.language.subtype}
              </Badge>
            )}
            <Badge size='sm' variant='outline'>
              <CalendarDays />
              {`Born in epoch ${current.language.birth_epoch}`}
            </Badge>
            <Badge size='sm' variant='outline'>
              <GitFork />
              {parent ? `Daughter of ${parent.language.name}` : 'A root tongue'}
            </Badge>
          </div>
          {current.description && (
            <Muted variant='caption' truncate={4}>
              {current.description}
            </Muted>
          )}
        </div>
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 md:grid-cols-4'>
        <MiniStat
          icon={WholeWord}
          label='Words'
          value={current.word_total}
          tone='gold'
        />
        <MiniStat
          icon={Users}
          label='Speaking peoples'
          value={current.speakers.length}
          tone='verdigris'
        />
        <MiniStat
          icon={CaseSensitive}
          label='Letters'
          value={node?.alphabet.length ?? 0}
          tone='info'
        />
        <MiniStat
          icon={GitFork}
          label='Daughters'
          value={daughters.length}
          tone='muted'
        />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-4 lg:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Sound signature</Label>
          <SoundSignature signature={node?.signature ?? null} />
        </div>
        {node && node.alphabet.length > 0 && (
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Alphabet</Label>
            <LetterTiles letters={node.alphabet} label='Alphabet' />
          </div>
        )}
      </div>
      {node && node.sample_names.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Names born in it</Label>
          <NameChips names={node.sample_names} />
        </div>
      )}
      {current.speakers.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Spoken by</Label>
          <PagedList
            items={current.speakers}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1'
            itemKey={(speaker) => speaker.id}
          >
            {(speaker) => (
              <EntityLink
                key={speaker.id}
                kind='entity'
                id={String(speaker.id)}
                showIcon
              >
                {speaker.name}
              </EntityLink>
            )}
          </PagedList>
        </div>
      )}
    </div>
  )
}

function WordRegister({ word }: { word: Lexeme }) {
  const move = useTongueAction(
    'word:register',
    (register: string) => ({
      lexeme_id: word.id,
      word_register: register as Lexeme['word_register'],
    }),
    'The word moves to another register'
  )
  return (
    <MindPicker
      label='Register'
      value={word.word_register}
      table={table(REGISTERS)}
      blocked={why(null, move.isPending)}
      onPick={(value) => move.mutate(value)}
    />
  )
}

function WordCard({ word, query }: { word: Lexeme; query: string }) {
  const Part = word.part_of_speech ? PART_ICON[word.part_of_speech] : null
  const register = REGISTERS[word.word_register]
  return (
    <li className='flex min-w-0 flex-col gap-1.5 rounded-lg border bg-background p-3'>
      <div className='flex min-w-0 items-start gap-2'>
        <Text
          as='span'
          weight='semibold'
          className='min-w-0 flex-1 font-display text-primary'
          truncate
        >
          <Highlight text={word.word} query={query} />
        </Text>
        {Part && word.part_of_speech && (
          <Badge size='sm' variant='outline'>
            <Part />
            {humanize(word.part_of_speech)}
          </Badge>
        )}
      </div>
      <Text as='span'>
        <Highlight text={word.meaning} query={query} />
      </Text>
      {word.example && (
        <div className='flex min-w-0 items-start gap-1.5'>
          <Quote
            aria-hidden='true'
            className='size-icon-xs shrink-0 text-muted-foreground'
          />
          <Muted as='span' variant='caption' italic>
            {word.example}
          </Muted>
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Muted as='span' variant='caption' truncate className='min-w-0 flex-1'>
          {word.etymology ??
            word.added_by?.name ??
            humanize(word.added_by_kind)}
        </Muted>
        <Badge size='sm' variant='outline'>{`E${word.epoch}`}</Badge>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Badge size='sm' variant='outline'>
          <register.icon />
          {register.label}
        </Badge>
        {word.proto_word && word.proto_word !== word.word && (
          <Muted as='span' variant='caption' italic truncate>
            {`from older ${word.proto_word}`}
          </Muted>
        )}
      </div>
      <WordRegister word={word} />
    </li>
  )
}

function Lexicon({ current }: { current: LanguageView }) {
  const [shown, setShown] = useState(WORD_STEP)
  const [part, setPart] = useState<PartOfSpeech | typeof ALL_PARTS>(ALL_PARTS)
  const [filter, setFilter] = useState('')
  const counts = useMemo(() => {
    const map = new Map<PartOfSpeech, number>()
    for (const word of current.words)
      if (word.part_of_speech)
        map.set(word.part_of_speech, (map.get(word.part_of_speech) ?? 0) + 1)
    return [...map.entries()].sort((left, right) => right[1] - left[1])
  }, [current.words])
  const needle = filter.trim().toLowerCase()
  const words = current.words.filter(
    (word) =>
      (part === ALL_PARTS || word.part_of_speech === part) &&
      (!needle ||
        word.word.toLowerCase().includes(needle) ||
        word.meaning.toLowerCase().includes(needle))
  )
  return (
    <Section
      id='languages-lexicon'
      title='Lexicon'
      description={`${formatInteger(current.word_total)} words, oldest first.`}
      level={3}
      actions={
        <Input
          type='search'
          leadingIcon={Search}
          placeholder={`Search ${current.language.name}`}
          aria-label={`Search ${current.language.name}`}
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
        />
      }
    >
      {counts.length > 1 && (
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Button
            size='sm'
            variant={part === ALL_PARTS ? 'secondary' : 'ghost'}
            aria-pressed={part === ALL_PARTS}
            onClick={() => setPart(ALL_PARTS)}
          >
            <BookA />
            {`All · ${current.words.length}`}
          </Button>
          {counts.map(([key, count]) => {
            const Icon = PART_ICON[key]
            return (
              <Button
                key={key}
                size='sm'
                variant={part === key ? 'secondary' : 'ghost'}
                aria-pressed={part === key}
                onClick={() => setPart(key)}
              >
                <Icon />
                {`${humanize(key)} · ${count}`}
              </Button>
            )
          })}
        </div>
      )}
      {words.length === 0 ? (
        <Muted>
          {current.words.length === 0
            ? 'No word has been recorded yet.'
            : 'No word matches.'}
        </Muted>
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2 2xl:grid-cols-3'>
          {words.slice(0, shown).map((word) => (
            <WordCard key={word.id} word={word} query={filter} />
          ))}
        </ul>
      )}
      {words.length > shown && (
        <Button
          variant='outline'
          className='self-start'
          onClick={() => setShown((count) => count + WORD_STEP)}
        >
          {`${formatInteger(words.length - shown)} more words`}
        </Button>
      )}
      {current.word_total > current.words.length && (
        <Muted variant='caption'>
          {`The first ${formatInteger(current.words.length)} of ${formatInteger(current.word_total)} words are shown; the book holds them all.`}
        </Muted>
      )}
    </Section>
  )
}

function EveryTongueSearch({
  languages,
  query,
  onQuery,
  onSelect,
}: {
  languages: LanguageView[]
  query: string
  onQuery: (query: string) => void
  onSelect: (id: number) => void
}) {
  const needle = query.trim().toLowerCase()
  const matches = useMemo(() => {
    if (!needle) return []
    return languages.flatMap((language) =>
      language.words
        .filter(
          (word) =>
            word.word.toLowerCase().includes(needle) ||
            word.meaning.toLowerCase().includes(needle)
        )
        .map((word) => ({ language, word }))
    )
  }, [languages, needle])
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Input
        type='search'
        leadingIcon={Search}
        placeholder='Search words and meanings in every tongue'
        aria-label='Search the lexicons'
        value={query}
        onChange={(event) => onQuery(event.target.value)}
      />
      {needle && (
        <div className='flex min-w-0 flex-col gap-2 rounded-xl border bg-card p-3'>
          <Label variant='overline'>
            {`${formatInteger(matches.length)} words found`}
          </Label>
          {matches.length === 0 ? (
            <Muted variant='caption'>No language has such a word yet.</Muted>
          ) : (
            <ul className='grid min-w-0 grid-cols-1 gap-1.5 md:grid-cols-2'>
              {matches.slice(0, MATCH_LIMIT).map(({ language, word }) => (
                <li
                  key={`${language.language.id}-${word.id}`}
                  className='min-w-0'
                >
                  <Button
                    variant='ghost'
                    size='tile'
                    onClick={() => onSelect(language.language.id)}
                  >
                    <Text as='span' weight='semibold' className='font-display'>
                      <Highlight text={word.word} query={query} />
                    </Text>
                    <Text as='span' truncate className='min-w-0 flex-1'>
                      <Highlight text={word.meaning} query={query} />
                    </Text>
                    <Badge size='sm' variant='outline'>
                      {language.language.name}
                    </Badge>
                  </Button>
                </li>
              ))}
            </ul>
          )}
          {matches.length > MATCH_LIMIT && (
            <Muted variant='caption'>
              {`${formatInteger(matches.length - MATCH_LIMIT)} more; narrow the search.`}
            </Muted>
          )}
        </div>
      )}
    </div>
  )
}

export function Dictionary({
  languages,
  nodes,
  selected,
  onSelect,
  query,
  onQuery,
}: DictionaryProps) {
  const current =
    languages.find((item) => item.language.id === selected) ?? languages[0]
  const node = nodes.find((item) => item.language.id === current?.language.id)
  if (!current)
    return (
      <EmptyState
        icon={BookA}
        title='No languages yet'
        description='Peoples speak and name things in their own tongues once they exist; sons of high rarity may also shape a language.'
      />
    )
  return (
    <div className='grid min-w-0 grid-cols-1 gap-6 lg:grid-cols-4'>
      <div className='min-w-0 lg:sticky lg:top-topbar lg:self-start'>
        <LanguageRail
          languages={languages}
          nodes={nodes}
          current={current.language.id}
          onSelect={onSelect}
        />
      </div>
      <div className='flex min-w-0 flex-col gap-6 lg:col-span-3'>
        <EveryTongueSearch
          languages={languages}
          query={query}
          onQuery={onQuery}
          onSelect={onSelect}
        />
        <LanguageHero current={current} node={node} nodes={nodes} />
        <Lexicon key={current.language.id} current={current} />
        <div className='grid min-w-0 grid-cols-1 gap-6 2xl:grid-cols-2'>
          <TranslationBox
            key={`translate-${current.language.id}`}
            languageId={current.language.id}
            languageName={current.language.name}
          />
          <AddWordsForm
            key={`words-${current.language.id}`}
            languageId={current.language.id}
            languageName={current.language.name}
          />
        </div>
      </div>
    </div>
  )
}
