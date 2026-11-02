import { useState } from 'react'
import { BookPlus, Plus, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { wordKindValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Section } from '@/components/domain'
import { useLoreGate } from '@/features/entity/actions/gate'
import { humanize } from '@/features/entity/actions/schema'
import { useLoreMutation } from '@/features/entity/api/mutations'
import {
  ANY_KIND,
  MEANING_MAX,
  type Row,
  WORDS_PER_ORDER_MAX,
  WORD_MAX,
  emptyRow,
  wordsOf,
} from './addWords'

export function AddWordsForm({
  languageId,
  languageName,
}: {
  languageId: number
  languageName: string
}) {
  const [rows, setRows] = useState<Row[]>([emptyRow(0)])
  const [nextKey, setNextKey] = useState(1)
  const gate = useLoreGate()
  const words = wordsOf(rows)
  const add = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/languages/{language_id}/words', {
          params: { path: { language_id: languageId } },
          body: { words },
        })
      ),
    onDone: () => {
      setRows([emptyRow(nextKey)])
      setNextKey((key) => key + 1)
    },
  })
  const update = (key: number, patch: Partial<Row>) =>
    setRows((current) =>
      current.map((row) => (row.key === key ? { ...row, ...patch } : row))
    )
  const blocked =
    gate.reason() ??
    (words.length === 0 ? 'Write at least one word and its meaning.' : null) ??
    (add.isPending ? 'Working on it.' : null)
  return (
    <Section
      id='languages-add-words'
      title={`Teach ${languageName} new words`}
      description='Empty, meaningless and already known words are skipped.'
      level={3}
    >
      <ul className='flex min-w-0 flex-col gap-2'>
        {rows.map((row, index) => (
          <li
            key={row.key}
            className='grid min-w-0 grid-cols-1 items-center gap-2 sm:grid-cols-4'
          >
            <Input
              aria-label={`Word ${index + 1}`}
              placeholder='Word'
              maxLength={WORD_MAX}
              value={row.word}
              onChange={(event) =>
                update(row.key, { word: event.target.value })
              }
            />
            <Input
              aria-label={`Meaning ${index + 1}`}
              placeholder='Meaning'
              maxLength={MEANING_MAX}
              value={row.meaning}
              className='sm:col-span-2'
              onChange={(event) =>
                update(row.key, { meaning: event.target.value })
              }
            />
            <div className='flex min-w-0 items-center gap-2'>
              <Select
                value={row.kind}
                onValueChange={(kind) => update(row.key, { kind })}
              >
                <SelectTrigger
                  className='min-w-0 flex-1'
                  aria-label={`Kind of word ${index + 1}`}
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ANY_KIND}>Any kind</SelectItem>
                  {wordKindValues.map((kind) => (
                    <SelectItem key={kind} value={kind}>
                      {humanize(kind)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant='ghost'
                size='icon'
                aria-label={`Remove word ${index + 1}`}
                disabled={rows.length === 1}
                disabledReason='At least one row stays.'
                onClick={() =>
                  setRows((current) =>
                    current.filter((item) => item.key !== row.key)
                  )
                }
              >
                <X />
              </Button>
            </div>
          </li>
        ))}
      </ul>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          variant='outline'
          disabled={rows.length >= WORDS_PER_ORDER_MAX}
          disabledReason={`At most ${WORDS_PER_ORDER_MAX} words at once.`}
          onClick={() => {
            setRows((current) => [...current, emptyRow(nextKey)])
            setNextKey((key) => key + 1)
          }}
        >
          <Plus />
          Another word
        </Button>
        <Button
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          aria-busy={add.isPending || undefined}
          onClick={() => add.mutate()}
        >
          <BookPlus />
          {words.length > 1 ? `Add ${words.length} words` : 'Add the word'}
        </Button>
      </div>
    </Section>
  )
}
