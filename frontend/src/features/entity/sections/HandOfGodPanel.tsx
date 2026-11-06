import { useMemo, useState } from 'react'
import {
  CircleSlash,
  CloudLightning,
  HandHeart,
  Lightbulb,
  Moon,
  Send,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ConfirmDialog, FormRow, Section, Paged } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Muted } from '@/components/typography'
import { CostChip } from '../actions/ActionCard'
import { type EntityContext, isThinking } from '../actions/context'
import { fixedCost, useLoreGate } from '../actions/gate'
import { optionsFor } from '../actions/pickers'
import { humanize } from '../actions/schema'
import { usePickerData } from '../actions/usePickerData'
import { useLoreMutation } from '../api/mutations'
import { useActionCatalogue, useCatalogue } from '../api/queries'
import {
  DISASTER_TYPES,
  DREAM_MAX_LENGTH,
  DREAM_MIN_LENGTH,
  NO_INTERVENTION_TYPES,
} from '../constants'
import {
  type Intervention,
  curseBlock,
  interventionCost,
  miracleBlock,
} from './handOfGod'

export function HandOfGodPanel({ ctx }: { ctx: EntityContext }) {
  const catalogue = useCatalogue()
  const actions = useActionCatalogue()
  const data = usePickerData()
  const gate = useLoreGate()
  const [knowledge, setKnowledge] = useState<number | null>(null)
  const [dream, setDream] = useState('')
  const [pending, setPending] = useState<{
    kind: Intervention
    option?: string
  } | null>(null)
  const item = actions.data?.find((action) => action.id === 'intervene')
  const dreamItem = actions.data?.find((action) => action.id === 'dream')
  const intervene = useLoreMutation({
    run: (input: {
      action: Intervention
      miracle?: string
      disaster?: string
      knowledge_id?: number
    }) =>
      unwrap(
        api.POST('/api/entities/{entity_id}/intervene', {
          params: { path: { entity_id: ctx.entity.id } },
          body: input as never,
        })
      ),
    success: 'Intervention done',
    onDone: () => setKnowledge(null),
  })
  const send = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/entities/{entity_id}/dream', {
          params: { path: { entity_id: ctx.entity.id } },
          body: { text: dream.trim() },
        })
      ),
    success: 'Dream sent; it sees it on its next turn',
    onDone: () => setDream(''),
  })
  const knowledgeOptions = useMemo(
    () => optionsFor({ source: 'knowledge', unknownOnly: true }, ctx, data),
    [ctx, data]
  )
  if (!ctx.canon || NO_INTERVENTION_TYPES.includes(ctx.type)) return null
  const thinking = isThinking(ctx.type)
  const reasonFor = (kind: Intervention) =>
    gate.reason({ cost: interventionCost(item?.cost, kind) }) ??
    (intervene.isPending ? 'Working on it.' : null)
  const miracles = catalogue.data?.enums.miracles ?? []
  const disasters = catalogue.data?.enums.disasters ?? []
  const run = (kind: Intervention, option?: string) => {
    if (kind === 'miracle') intervene.mutate({ action: kind, miracle: option })
    else if (kind === 'disaster')
      intervene.mutate({ action: kind, disaster: option })
    else if (kind === 'teach_knowledge' && knowledge !== null)
      intervene.mutate({ action: kind, knowledge_id: knowledge })
    else intervene.mutate({ action: kind })
  }
  const costText = (kind: Intervention) => {
    const amount = interventionCost(item?.cost, kind)
    return amount === null ? null : <CostChip text={`${amount} essence`} />
  }
  const dreamCost = fixedCost(dreamItem?.cost)
  const dreamReason =
    gate.reason({ cost: dreamCost }) ??
    (dream.trim().length < DREAM_MIN_LENGTH
      ? 'The dream must have content.'
      : null) ??
    (send.isPending ? 'Working on it.' : null)
  return (
    <Section
      id='section-hand'
      title='Hand of God'
      description='Intervene directly with your divine essence.'
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <div className='flex min-w-0 items-center gap-2'>
          <Label variant='overline'>Miracle</Label>
          {costText('miracle')}
        </div>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Paged items={miracles}>
            {(miracle) => {
              const reason = reasonFor('miracle') ?? miracleBlock(ctx, miracle)
              return (
                <Button
                  key={miracle}
                  variant='outline'
                  disabled={reason !== null}
                  disabledReason={reason ?? undefined}
                  onClick={() => run('miracle', miracle)}
                >
                  <HandHeart />
                  {humanize(miracle)}
                </Button>
              )
            }}
          </Paged>
        </div>
      </div>
      {DISASTER_TYPES.includes(ctx.type) && (
        <div className='flex min-w-0 flex-col gap-2'>
          <div className='flex min-w-0 items-center gap-2'>
            <Label variant='overline'>Disaster</Label>
            {costText('disaster')}
          </div>
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Paged items={disasters}>
              {(disaster) => {
                const reason = reasonFor('disaster')
                return (
                  <Button
                    key={disaster}
                    variant='destructive'
                    disabled={reason !== null}
                    disabledReason={reason ?? undefined}
                    onClick={() =>
                      setPending({ kind: 'disaster', option: disaster })
                    }
                  >
                    <CloudLightning />
                    {humanize(disaster)}
                  </Button>
                )
              }}
            </Paged>
          </div>
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Label variant='overline'>Curse</Label>
        {costText('curse')}
        {(() => {
          const reason = reasonFor('curse') ?? curseBlock(ctx)
          return (
            <Button
              variant='destructive'
              disabled={reason !== null}
              disabledReason={reason ?? undefined}
              onClick={() => setPending({ kind: 'curse' })}
            >
              <CircleSlash />
              Curse
            </Button>
          )
        })()}
      </div>
      {thinking &&
        (data.knowledge.length > 0 || knowledgeOptions.length > 0) && (
          <FormRow label='Teach knowledge'>
            {(id) =>
              knowledgeOptions.length === 0 ? (
                <Muted>It already knows all knowledge in the world.</Muted>
              ) : (
                <div className='flex w-full min-w-0 flex-col gap-2 sm:flex-row sm:items-center'>
                  <div className='min-w-0 sm:flex-1'>
                    <RecordCombobox
                      id={id}
                      options={knowledgeOptions}
                      value={knowledge === null ? null : String(knowledge)}
                      onChange={(value) =>
                        setKnowledge(value === null ? null : Number(value))
                      }
                      placeholder='Choose knowledge'
                      aria-label='Knowledge to teach'
                    />
                  </div>
                  {(() => {
                    const reason =
                      reasonFor('teach_knowledge') ??
                      (knowledge === null ? 'Choose knowledge first.' : null)
                    return (
                      <Button
                        variant='outline'
                        disabled={reason !== null}
                        disabledReason={reason ?? undefined}
                        onClick={() => run('teach_knowledge')}
                      >
                        <Lightbulb />
                        Teach
                        {costText('teach_knowledge')}
                      </Button>
                    )
                  })()}
                </div>
              )
            }
          </FormRow>
        )}
      {thinking && (
        <div className='flex min-w-0 flex-col gap-2'>
          <div className='flex min-w-0 items-center gap-2'>
            <Moon
              aria-hidden='true'
              className='size-icon-sm text-muted-foreground'
            />
            <Label variant='overline'>Send a dream</Label>
            {dreamItem && <CostChip text={dreamItem.cost} />}
          </div>
          <Muted variant='caption'>{`${ctx.entity.name} sees it on its next turn and reads it in its own way.`}</Muted>
          <Textarea
            aria-label='The dream'
            maxLength={DREAM_MAX_LENGTH}
            placeholder='Describe what happens, where, and what it changes…'
            value={dream}
            onChange={(event) => setDream(event.target.value)}
          />
          <Button
            className='self-start'
            disabled={dreamReason !== null}
            disabledReason={dreamReason ?? undefined}
            onClick={() => send.mutate()}
          >
            <Send />
            Send the dream
          </Button>
        </div>
      )}
      <ConfirmDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={
          pending?.kind === 'curse'
            ? `Curse ${ctx.entity.name}?`
            : `Send ${humanize(pending?.option ?? '')}?`
        }
        desc={
          pending?.kind === 'curse'
            ? 'Its fortunes fall and the chronicle remembers who did it.'
            : `${ctx.entity.name} and those who live there will suffer it.`
        }
        destructive
        confirmText={pending?.kind === 'curse' ? 'Curse' : 'Send'}
        isLoading={intervene.isPending}
        handleConfirm={() => {
          if (pending) run(pending.kind, pending.option)
          setPending(null)
        }}
      />
    </Section>
  )
}
