import { ArrowDown } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  EntityLink,
  PagedList,
  Section,
  ShowMore,
  useShowMore,
  Paged,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { type EntityContext } from '../actions/context'
import { humanize } from '../actions/schema'
import { useLanguageViews } from '../api/queries'
import { type BondView, type NodeRef } from '../api/types'

function bondsOf(
  ctx: EntityContext,
  kinds: string[],
  outgoing: boolean
): BondView[] {
  return ctx.bonds.filter(
    (bond) =>
      kinds.includes(bond.kind) &&
      bond.outgoing === outgoing &&
      bond.other &&
      bond.state === 'active'
  )
}

const REFS_SHOWN = 20
const WORDS_SHOWN = 12
const CONTENTS_SHOWN = 12

function RefList({ refs }: { refs: NodeRef[] }) {
  return (
    <PagedList
      items={refs}
      initial={REFS_SHOWN}
      className='flex min-w-0 flex-wrap gap-2'
      itemKey={(ref) => ref.id}
    >
      {(ref) => (
        <li className='min-w-0'>
          <Badge variant='outline' asChild>
            <EntityLink kind='entity' id={String(ref.id)}>
              {ref.name}
            </EntityLink>
          </Badge>
        </li>
      )}
    </PagedList>
  )
}

function Lexicon({ ctx }: { ctx: EntityContext }) {
  const languages = useLanguageViews(ctx.type === 'language')
  if (ctx.type !== 'language') return null
  const view = languages.data?.find(
    (item) => item.language.id === ctx.entity.id
  )
  if (!view) return null
  return <LexiconTable view={view} />
}

function LexiconTable({
  view,
}: {
  view: NonNullable<ReturnType<typeof useLanguageViews>['data']>[number]
}) {
  const page = useShowMore(view.words, WORDS_SHOWN, WORDS_SHOWN * 2)
  const words = page.visible
  return (
    <Section
      id='section-lexicon'
      title='Lexicon'
      description={`${formatInteger(view.word_total)} words · spoken by ${view.speakers.map((item) => item.name).join(', ') || 'nobody yet'}`}
    >
      {words.length === 0 ? (
        <Muted>No word has been recorded yet.</Muted>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Word</TableHead>
              <TableHead>Meaning</TableHead>
              <TableHead>Origin</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {words.map((word) => (
              <TableRow key={word.id}>
                <TableCell>
                  <Text as='span' weight='medium'>
                    {word.word}
                  </Text>
                </TableCell>
                <TableCell>
                  <Text as='span'>{word.meaning}</Text>
                  {word.part_of_speech && (
                    <Muted
                      as='span'
                      variant='caption'
                    >{` · ${humanize(word.part_of_speech)}`}</Muted>
                  )}
                  {word.example && (
                    <Muted
                      as='span'
                      variant='caption'
                      italic
                    >{` · ${word.example}`}</Muted>
                  )}
                </TableCell>
                <TableCell>
                  <Muted as='span' variant='caption'>
                    {word.etymology ??
                      word.added_by?.name ??
                      humanize(word.added_by_kind)}
                  </Muted>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      <ShowMore state={page} noun={['word', 'words']} />
      {view.word_total > view.words.length && (
        <Muted variant='caption'>
          The full lexicon is on the Languages screen.
        </Muted>
      )}
    </Section>
  )
}

export function EntityRecords({ ctx }: { ctx: EntityContext }) {
  const languages = bondsOf(ctx, ['speaks'], true)
  const owns = bondsOf(ctx, ['owns'], true)
  const produced = bondsOf(ctx, ['produced', 'built'], true)
  const ancestors = ctx.detail.insight.ancestors ?? []
  const descendants = ctx.detail.insight.descendants ?? []
  const contents = ctx.detail.contents
  return (
    <>
      {languages.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Label>Speaks</Label>
          <RefList refs={languages.map((bond) => bond.other as NodeRef)} />
        </div>
      )}
      <Lexicon ctx={ctx} />
      {owns.length > 0 && (
        <Section id='section-owns' title='What it owns'>
          <RefList refs={owns.map((bond) => bond.other as NodeRef)} />
        </Section>
      )}
      {(ancestors.length > 0 || descendants.length > 0) && (
        <Section id='section-lineage' title='Lineage'>
          <ol className='flex min-w-0 flex-col items-start gap-1'>
            <Paged items={ancestors} as='li'>
              {(ref) => (
                <li
                  key={`a-${ref.id}`}
                  className='flex min-w-0 items-center gap-2'
                >
                  <EntityLink kind='entity' id={String(ref.id)}>
                    {ref.name}
                  </EntityLink>
                  <ArrowDown
                    aria-hidden='true'
                    className='size-icon-xs text-muted-foreground'
                  />
                </li>
              )}
            </Paged>
            <li>
              <Text as='strong' weight='semibold'>
                {ctx.entity.name}
              </Text>
            </li>
            <Paged items={descendants}>
              {(ref) => (
                <li
                  key={`d-${ref.id}`}
                  className='flex min-w-0 items-center gap-2'
                >
                  <ArrowDown
                    aria-hidden='true'
                    className='size-icon-xs text-muted-foreground'
                  />
                  <EntityLink kind='entity' id={String(ref.id)}>
                    {ref.name}
                  </EntityLink>
                </li>
              )}
            </Paged>
          </ol>
        </Section>
      )}
      {produced.length > 0 && (
        <Section id='section-produced' title='Produced and founded'>
          <RefList refs={produced.map((bond) => bond.other as NodeRef)} />
        </Section>
      )}
      {contents.length > 0 && (
        <Section
          id='section-inside'
          title='Inside'
          description={
            ctx.detail.content_total > contents.length
              ? `${formatInteger(contents.length)} of ${formatInteger(ctx.detail.content_total)} shown; the Atlas lists all.`
              : undefined
          }
        >
          <PagedList
            items={contents}
            initial={CONTENTS_SHOWN}
            className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
            itemKey={(item) => item.id}
          >
            {(item) => (
              <li className='flex min-w-0 items-center gap-2 rounded-md border bg-card px-2.5 py-1.5'>
                <Badge size='sm' variant='outline'>
                  {humanize(item.entity_type)}
                </Badge>
                <EntityLink kind='entity' id={String(item.id)}>
                  {item.name}
                </EntityLink>
                {item.subtype && (
                  <Muted as='span' variant='caption' truncate>
                    {item.subtype}
                  </Muted>
                )}
              </li>
            )}
          </PagedList>
        </Section>
      )}
    </>
  )
}
