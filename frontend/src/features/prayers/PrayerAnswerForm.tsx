import { useState } from 'react'
import { HandHeart, Moon, Sparkles } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Muted } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

const QUICK_SHARES = [0.25, 0.5, 1] as const

type PrayerAnswerFormProps = {
  messageId: number
  mortal: boolean
}

export function PrayerAnswerForm({ messageId, mortal }: PrayerAnswerFormProps) {
  const [text, setText] = useState('')
  const [essence, setEssence] = useState('0')
  const rule = useRuleLookup()
  const { reason, essence: available } = useGodGate()
  const cap = rule('god_actions.prayer_essence_cap')
  const max = Math.max(0, Math.min(cap ?? available, available))
  const gift = essence === '' ? 0 : Number(essence)
  const answer = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/prayers/{message_id}/answer', {
          params: { path: { message_id: messageId } },
          body: { text: text.trim(), essence: gift },
        })
      ),
    success: gift > 0 ? `Answer and ${gift} essence sent` : 'Answer sent',
  })
  const invalid =
    !Number.isInteger(gift) || gift < 0
      ? 'Give a whole number of essence.'
      : gift > max
        ? `You can give at most ${max} essence to one prayer.`
        : !text.trim() && gift === 0
          ? 'Write an answer or give essence.'
          : null
  const textId = `prayer-text-${messageId}`
  const essenceId = `prayer-essence-${messageId}`
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-3'>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
        <div className='flex min-w-0 flex-col gap-1 sm:col-span-2'>
          <FieldLabel htmlFor={textId}>
            {mortal ? 'What should fall into their dream?' : 'Your answer'}
          </FieldLabel>
          <Input
            id={textId}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1'>
          <FieldLabel
            htmlFor={essenceId}
          >{`Give essence (at most ${max})`}</FieldLabel>
          <Input
            id={essenceId}
            type='number'
            min={0}
            max={max}
            value={essence}
            onChange={(event) => setEssence(event.target.value)}
          />
          {max > 0 && (
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              {QUICK_SHARES.map((share) => {
                const value = Math.max(1, Math.floor(max * share))
                return (
                  <Button
                    key={share}
                    type='button'
                    variant={gift === value ? 'default' : 'outline'}
                    size='sm'
                    onClick={() => setEssence(String(value))}
                  >
                    <Sparkles />
                    {value}
                  </Button>
                )
              })}
            </div>
          )}
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <ActionButton
          label={mortal ? 'Answer with a dream' : 'Answer'}
          icon={mortal ? Moon : HandHeart}
          variant='default'
          cost={gift > 0 ? gift : undefined}
          blocked={reason({ cost: gift }) ?? invalid}
          pending={answer.isPending}
          onRun={() => answer.mutate()}
        />
        <Muted variant='caption'>
          {mortal
            ? 'Your gift raises their prosperity, fertility, defence and health, and binds them to a cult of you.'
            : 'The essence joins their own; what overflows is lost. Gifts also raise their loyalty.'}
        </Muted>
      </div>
    </div>
  )
}
