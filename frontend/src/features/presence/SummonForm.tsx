import { type KeyboardEvent, useId, useRef, useState } from 'react'
import { Check, Dot, Loader2, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { READ_ONLY_MESSAGE, isReadOnly } from '@/api/readOnly'
import { Button } from '@/components/ui/button'
import { Medallion, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useOpenSession } from './api'
import {
  GUISE_LOOK,
  GUISE_ORDER,
  NO_MODEL,
  RECORD_LOOK,
  RECORD_ORDER,
  type RecordLook,
} from './looks'
import {
  type PresenceGuise,
  type PresenceRecord,
  type SpeakerCard,
} from './types'

const STEP_KEYS: Record<string, number> = {
  ArrowRight: 1,
  ArrowDown: 1,
  ArrowLeft: -1,
  ArrowUp: -1,
}

function useRovingChoice<T extends string>(
  options: readonly T[],
  value: T,
  onChange: (value: T) => void
) {
  const refs = useRef<(HTMLButtonElement | null)[]>([])
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = STEP_KEYS[event.key]
    if (step === undefined) return
    event.preventDefault()
    const index = options.indexOf(value)
    const next = (index + step + options.length) % options.length
    onChange(options[next])
    refs.current[next]?.focus()
  }
  return { refs, onKeyDown }
}

function keepsOf(
  record: PresenceRecord,
  look: RecordLook,
  canAct: boolean
): readonly string[] {
  if (record !== 'on_record' || canAct) return look.keeps
  return [
    ...look.keeps.slice(0, -1),
    'It reads the world only: the dead and foreign gods never act.',
  ]
}

function GuisePicker({
  value,
  onChange,
}: {
  value: PresenceGuise
  onChange: (value: PresenceGuise) => void
}) {
  const labelId = useId()
  const roving = useRovingChoice(GUISE_ORDER, value, onChange)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-col'>
        <Label id={labelId} variant='gilded'>
          How you appear
        </Label>
        <Muted variant='caption'>
          Who it believes it hears. The guise holds for the whole audience.
        </Muted>
      </div>
      <div
        role='radiogroup'
        aria-labelledby={labelId}
        onKeyDown={roving.onKeyDown}
        className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 2xl:grid-cols-4'
      >
        {GUISE_ORDER.map((guise, index) => {
          const look = GUISE_LOOK[guise]
          const chosen = guise === value
          return (
            <Button
              key={guise}
              ref={(element) => {
                roving.refs.current[index] = element
              }}
              type='button'
              role='radio'
              aria-checked={chosen}
              tabIndex={chosen ? 0 : -1}
              variant='outline'
              size='card'
              data-domain='presence-guise'
              data-guise={guise}
              onClick={() => onChange(guise)}
            >
              <span className='flex min-w-0 items-center justify-between gap-2'>
                <Medallion icon={look.icon} tone={look.tone} />
                {chosen && (
                  <Check aria-hidden='true' className='text-primary' />
                )}
              </span>
              <Text as='span' weight='semibold' className='font-display'>
                {look.label}
              </Text>
              <Muted as='span' variant='caption'>
                {look.line}
              </Muted>
            </Button>
          )
        })}
      </div>
    </div>
  )
}

function RecordChoice({
  value,
  onChange,
  canAct,
}: {
  value: PresenceRecord
  onChange: (value: PresenceRecord) => void
  canAct: boolean
}) {
  const labelId = useId()
  const roving = useRovingChoice(RECORD_ORDER, value, onChange)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-col'>
        <Label id={labelId} variant='gilded'>
          What is kept
        </Label>
        <Muted variant='caption'>
          Chosen once for the audience; it cannot change while it lasts.
        </Muted>
      </div>
      <div
        role='radiogroup'
        aria-labelledby={labelId}
        onKeyDown={roving.onKeyDown}
        className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'
      >
        {RECORD_ORDER.map((record, index) => {
          const look = RECORD_LOOK[record]
          const chosen = record === value
          return (
            <Button
              key={record}
              ref={(element) => {
                roving.refs.current[index] = element
              }}
              type='button'
              role='radio'
              aria-checked={chosen}
              tabIndex={chosen ? 0 : -1}
              variant='outline'
              size='card'
              data-domain='presence-record'
              data-record={record}
              onClick={() => onChange(record)}
            >
              <span className='flex min-w-0 items-center gap-2.5'>
                <Medallion icon={look.icon} tone={look.tone} size='sm' />
                <span className='flex min-w-0 flex-1 flex-col'>
                  <Text as='span' weight='semibold' className='font-display'>
                    {look.label}
                  </Text>
                  <Muted as='span' variant='caption'>
                    {look.line}
                  </Muted>
                </span>
                {chosen && (
                  <Check aria-hidden='true' className='text-primary' />
                )}
              </span>
              <span className='flex min-w-0 flex-col gap-1'>
                {keepsOf(record, look, canAct).map((line) => (
                  <span key={line} className='flex min-w-0 items-start gap-1.5'>
                    <Dot
                      aria-hidden='true'
                      className='size-icon-sm shrink-0 text-primary'
                    />
                    <Text as='span' variant='caption'>
                      {line}
                    </Text>
                  </span>
                ))}
              </span>
            </Button>
          )
        })}
      </div>
    </div>
  )
}

export function SummonForm({
  speaker,
  modelEnabled,
}: {
  speaker: SpeakerCard
  modelEnabled: boolean
}) {
  const [guise, setGuise] = useState<PresenceGuise>('creator')
  const [record, setRecord] = useState<PresenceRecord>('on_record')
  const open = useOpenSession()
  const reason = isReadOnly()
    ? READ_ONLY_MESSAGE
    : !modelEnabled
      ? NO_MODEL
      : open.isPending
        ? `Summoning ${speaker.name}.`
        : null
  const summon = () =>
    open.mutate(
      { node_id: speaker.node_id, guise, record },
      {
        onSuccess: () =>
          toast.success(`${speaker.name} stands before you`, {
            description: `${GUISE_LOOK[guise].heard} ${RECORD_LOOK[record].line}`,
          }),
        onError: (error) => toast.error(error.message),
      }
    )
  return (
    <Section
      id='presence-summon'
      title={`Summon ${speaker.name}`}
      icon={Sparkles}
      description={
        speaker.dead
          ? `${speaker.name} is dead. Called back, it knows it died, when and how, and speaks as one returned.`
          : `${speaker.name} answers as itself, from its own mind, memories and place in the world.`
      }
    >
      <GuisePicker value={guise} onChange={setGuise} />
      <RecordChoice
        value={record}
        onChange={setRecord}
        canAct={speaker.can_act}
      />
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-3 rounded-md surface-well px-3 py-2.5'>
        <Muted variant='caption' className='min-w-0 flex-1 basis-60'>
          {`${GUISE_LOOK[guise].heard} ${RECORD_LOOK[record].line}`}
        </Muted>
        <Button
          size='lg'
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={summon}
        >
          {open.isPending ? <Loader2 className='animate-spin' /> : <Sparkles />}
          {`Summon ${speaker.name}`}
        </Button>
      </div>
    </Section>
  )
}
