import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Languages } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components, partOfSpeechValues } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { formatInteger } from '@/lib/format'
import {
  type ViewerStorageKey,
  storeItem,
  storedItem,
  viewerKey,
} from '@/lib/universeStorage'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { KeyValueList, Paged, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { READ_ONLY_REASON } from '@/features/entity/actions/gate'
import { wordOf } from '@/features/entity/affairs/labels'
import { loreKeys } from '@/features/entity/api/keys'
import { useWorldState } from '@/features/entity/api/queries'
import { modelBlock } from '@/features/providers/modelReadiness'

type Translation = components['schemas']['TranslationOutput']

const TEXT_MAX = 2000
const AVERAGE_KEY: ViewerStorageKey = 'aerona.translation.average-ms'
const MS_PER_SECOND = 1000
const drafts = new Map<number, string>()

function readAverage(): number | null {
  try {
    const value = Number(storedItem(viewerKey(AVERAGE_KEY)))
    return Number.isFinite(value) && value > 0 ? value : null
  } catch {
    return null
  }
}

function writeAverage(duration: number) {
  try {
    const previous = readAverage()
    storeItem(
      viewerKey(AVERAGE_KEY),
      String(previous ? Math.round((previous + duration) / 2) : duration)
    )
  } catch {
    return
  }
}

function Elapsed({ since }: { since: number }) {
  const [now, setNow] = useState(since)
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), MS_PER_SECOND)
    return () => window.clearInterval(timer)
  }, [])
  const average = readAverage()
  const seconds = Math.max(0, Math.round((now - since) / MS_PER_SECOND))
  return (
    <Muted variant='caption' aria-live='polite'>
      {average
        ? `Translating… ${formatInteger(seconds)}s of about ${formatInteger(Math.round(average / MS_PER_SECOND))}s`
        : `Translating… ${formatInteger(seconds)}s`}
    </Muted>
  )
}

export function TranslationBox({
  languageId,
  languageName,
}: {
  languageId: number
  languageName: string
}) {
  const queryClient = useQueryClient()
  const state = useWorldState()
  const [text, setText] = useState(drafts.get(languageId) ?? '')
  const [started, setStarted] = useState<number | null>(null)
  const [result, setResult] = useState<Translation | null>(null)
  const startedAt = useRef<number | null>(null)
  const translate = useMutation({
    writes: [
      { method: 'POST', path: '/api/languages/{language_id}/translate' },
    ],
    mutationFn: () =>
      unwrap(
        api.POST('/api/languages/{language_id}/translate', {
          params: { path: { language_id: languageId } },
          body: { text: text.trim() },
        })
      ),
    onMutate: () => {
      startedAt.current = Date.now()
      setStarted(startedAt.current)
    },
    onSuccess: (output) => {
      if (startedAt.current) writeAverage(Date.now() - startedAt.current)
      setResult(output)
      toast.success(`Translated into ${languageName}`)
      void queryClient.invalidateQueries({ queryKey: loreKeys.languages })
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : String(error)),
    onSettled: () => setStarted(null),
  })
  const reason =
    (state.data?.read_only ? READ_ONLY_REASON : null) ??
    modelBlock(state.data, 'writing') ??
    (text.trim() === '' ? 'Write a sentence first.' : null) ??
    (translate.isPending ? 'Translating.' : null)
  return (
    <Section
      id='languages-translate'
      title={`Say it in ${languageName}`}
      description='The scribe translates, and new words enter the lexicon.'
      level={3}
    >
      <form
        className='flex min-w-0 flex-col gap-2'
        onSubmit={(event) => {
          event.preventDefault()
          if (reason === null) translate.mutate()
        }}
      >
        <Textarea
          act={translate}
          aria-label={`Text to translate into ${languageName}`}
          maxLength={TEXT_MAX}
          placeholder='A sentence to translate'
          value={text}
          onChange={(event) => {
            drafts.set(languageId, event.target.value)
            setText(event.target.value)
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              if (reason === null) translate.mutate()
            }
          }}
        />
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            act={translate}
            type='submit'
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
          >
            <Languages />
            Translate
          </Button>
          {started !== null && <Elapsed since={started} />}
        </div>
      </form>
      {result && (
        <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
          <Text variant='prose' weight='semibold'>
            {result.translation}
          </Text>
          <Muted italic>{result.pronunciation}</Muted>
          {result.word_by_word.length > 0 && (
            <KeyValueList
              items={result.word_by_word.map((gloss, index) => ({
                key: `${gloss.word}-${index}`,
                label: gloss.word,
                value: gloss.meaning,
              }))}
            />
          )}
          {result.new_words.length > 0 && (
            <div className='flex min-w-0 flex-col gap-1'>
              <Label variant='overline'>New words</Label>
              <ul className='flex min-w-0 flex-col gap-1'>
                <Paged items={result.new_words} as='li'>
                  {(word, index) => (
                    <Text as='li' key={`${word.word}-${index}`}>
                      <Text as='strong' weight='semibold'>
                        {word.word}
                      </Text>
                      {` · ${word.meaning} · ${wordOf(partOfSpeechValues, word.kind)} · ${word.origin}`}
                    </Text>
                  )}
                </Paged>
              </ul>
            </div>
          )}
          {result.note && <Muted variant='caption'>{result.note}</Muted>}
        </div>
      )}
    </Section>
  )
}
