import { useMemo, useState } from 'react'
import {
  BookOpen,
  Check,
  GraduationCap,
  Lock,
  Plus,
  Sparkles,
  TriangleAlert,
  X,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { knowledgeBranchValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { EmptyState, EntityLink, Section, StatBar } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { type LearningCard, table, useLearning, words } from './api'
import { busyOf } from './model'

const MAX_LEVEL = 10

function LevelRow({
  holderId,
  row,
  blocked,
}: {
  holderId: number
  row: LearningCard['levels'][number]
  blocked: string | null
}) {
  const [draft, setDraft] = useState(String(row.level))
  const set = useGodAction<number>({
    run: (level) =>
      unwrap(
        api.POST('/api/actions/research:level', {
          body: { holder_id: holderId, branch: row.branch, level },
        })
      ),
  })
  const busy = busyOf(blocked, set.isPending)
  return (
    <li
      data-surface='HolderLevel'
      className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-2'
    >
      <Text as='span' weight='semibold' className='min-w-28'>
        {words(row.branch)}
      </Text>
      <StatBar label={`level ${row.level}`} value={row.level} max={MAX_LEVEL} />
      <Muted
        as='span'
        variant='caption'
      >{`${row.practitioners} practise it`}</Muted>
      {!row.open && <Badge variant='warning'>gate shut</Badge>}
      {row.secret && <Badge variant='outline'>secret</Badge>}
      <Input
        className='w-20'
        type='number'
        min={0}
        value={draft}
        aria-label={`${words(row.branch)} level`}
        onChange={(event) => setDraft(event.target.value)}
      />
      <Button
        size='icon'
        variant='ghost'
        aria-label={`Set ${words(row.branch)}`}
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => set.mutate(Math.max(0, Math.round(Number(draft) || 0)))}
      >
        <Check />
      </Button>
    </li>
  )
}

function TechniqueTile({
  holderId,
  row,
  blocked,
}: {
  holderId: number
  row: LearningCard['techniques'][number]
  blocked: string | null
}) {
  const set = useGodAction<{ held: boolean; secret: boolean }>({
    run: ({ held, secret }) =>
      unwrap(
        api.POST('/api/actions/research:technique', {
          body: { holder_id: holderId, technique: row.technique, held, secret },
        })
      ),
  })
  const busy = busyOf(blocked, set.isPending)
  return (
    <li
      data-surface='TechniqueNode'
      className={`flex min-w-0 flex-col gap-1 rounded-lg border p-2 ${row.known ? 'border-primary bg-primary/10' : row.reachable ? 'bg-muted/30' : 'opacity-70'}`}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {row.known ? (
          <Sparkles aria-hidden='true' className='size-icon-sm text-primary' />
        ) : (
          <Lock
            aria-hidden='true'
            className='size-icon-sm text-muted-foreground'
          />
        )}
        <Text as='span' weight='semibold'>
          {row.label}
        </Text>
        <Badge variant='outline'>{`${words(row.branch)} ${row.level}`}</Badge>
        {row.reachable && !row.known && (
          <Badge variant='info'>within reach</Badge>
        )}
      </div>
      <Muted>{row.effect}</Muted>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {row.known ? (
          <>
            <label className='flex items-center gap-2'>
              <Switch
                checked={row.secret}
                disabled={busy !== null}
                aria-label='Keep it secret'
                onCheckedChange={(secret) => set.mutate({ held: true, secret })}
              />
              <Text as='span'>secret</Text>
            </label>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => set.mutate({ held: false, secret: false })}
            >
              <X />
              Forget it
            </Button>
          </>
        ) : (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => set.mutate({ held: true, secret: false })}
          >
            <Plus />
            Teach it
          </Button>
        )}
      </div>
    </li>
  )
}

function Body({
  card,
  blocked,
}: {
  card: LearningCard
  blocked: string | null
}) {
  const [branch, setBranch] = useState('')
  const add = useGodAction<string>({
    run: (chosen) =>
      unwrap(
        api.POST('/api/actions/research:level', {
          body: {
            holder_id: card.holder_id,
            branch: chosen as 'agriculture',
            level: 1,
          },
        })
      ),
  })
  const groups = useMemo(() => {
    const found = new Map<string, LearningCard['techniques']>()
    for (const row of card.techniques)
      found.set(row.branch, [...(found.get(row.branch) ?? []), row])
    return [...found.entries()]
  }, [card.techniques])
  const busy = busyOf(blocked, add.isPending)
  const known = card.levels.map((row) => row.branch)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Label variant='overline'>Branches of learning</Label>
      {card.levels.length === 0 && (
        <Muted>They have learned nothing yet.</Muted>
      )}
      <ul className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'>
        {card.levels.map((row) => (
          <LevelRow
            key={row.branch}
            holderId={card.holder_id}
            row={row}
            blocked={blocked}
          />
        ))}
      </ul>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <MindPicker
          label='Open a branch'
          value={branch}
          table={table(
            knowledgeBranchValues.filter((item) => !known.includes(item))
          )}
          blocked={busy}
          placeholder='Choose'
          onPick={setBranch}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || branch === ''}
          disabledReason={
            busy ?? (branch === '' ? 'Choose a branch' : undefined)
          }
          onClick={() => add.mutate(branch)}
        >
          <Plus />
          Begin it
        </Button>
      </div>
      {card.books.length > 0 && (
        <div
          data-surface='HolderBooks'
          className='flex min-w-0 flex-wrap items-center gap-2'
        >
          <BookOpen
            aria-hidden='true'
            className='size-icon-sm text-muted-foreground'
          />
          {card.books.map((book) => (
            <EntityLink key={book.id} kind='entity' id={String(book.id)}>
              {book.name}
            </EntityLink>
          ))}
        </div>
      )}
      <div data-surface='TechGraph' className='flex min-w-0 flex-col gap-3'>
        <Label variant='overline'>Techniques</Label>
        {groups.map(([name, rows]) => (
          <div key={name} className='flex min-w-0 flex-col gap-2'>
            <Text as='span' weight='semibold'>
              {words(name)}
            </Text>
            <ul className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3'>
              {rows.map((row) => (
                <TechniqueTile
                  key={row.technique}
                  holderId={card.holder_id}
                  row={row}
                  blocked={blocked}
                />
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}

export function LearningSection({
  holderId,
  readOnlyReason,
}: {
  holderId: number
  readOnlyReason?: string | null
}) {
  const view = useLearning(holderId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  return (
    <Section
      id='section-learning'
      title='Learning'
      description='Levels of knowledge, the techniques they open, and the books that keep them.'
      icon={GraduationCap}
    >
      {view.isPending && <Muted>Reading what they know…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Their learning could not be read'
          description={view.error.message}
        />
      )}
      {view.data && <Body card={view.data} blocked={blocked} />}
    </Section>
  )
}
