import { useState } from 'react'
import { Flame } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Label as FieldLabel } from '@/components/ui/label'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Muted } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { type CreatorPassion, type CreatorReputation } from './api'

export function PassionsForm({
  reputation,
}: {
  reputation: CreatorReputation
}) {
  const [chosen, setChosen] = useState<CreatorPassion[]>(reputation.passions)
  const rule = useRuleLookup()
  const limit = rule('reputation.max_passions')
  const { reason } = useGodGate()
  const declare = useGodAction({
    run: (body: { passions: CreatorPassion[]; automatic: boolean }) =>
      unwrap(api.PUT('/api/creator/passions', { body })),
    success: (_result, body) =>
      body.automatic
        ? 'Your passions are read from your deeds again'
        : 'Your passions were declared',
  })
  const names = new Map(
    reputation.all_passions.map((info) => [info.passion, info])
  )
  const overLimit = limit !== undefined && chosen.length > limit
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        {reputation.passions.map((passion) => (
          <Tooltip key={passion}>
            <TooltipTrigger asChild>
              <Badge variant='default'>
                {names.get(passion)?.name ?? passion}
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              {names.get(passion)?.hint ?? passion}
            </TooltipContent>
          </Tooltip>
        ))}
        <Muted variant='caption'>
          {reputation.automatic
            ? 'Read from your recent deeds'
            : 'Chosen by you'}
        </Muted>
      </div>
      <Collapsible className='flex min-w-0 flex-col gap-3'>
        <CollapsibleTrigger asChild>
          <Button variant='ghost' size='sm' className='self-start'>
            <Flame />
            Choose your passions yourself
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
          <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            {reputation.all_passions.map((info) => {
              const id = `passion-${info.passion}`
              const checked = chosen.includes(info.passion)
              return (
                <li
                  key={info.passion}
                  className='flex min-w-0 items-start gap-2'
                >
                  <Checkbox
                    id={id}
                    checked={checked}
                    onCheckedChange={(value) =>
                      setChosen(
                        value === true
                          ? [...chosen, info.passion]
                          : chosen.filter((item) => item !== info.passion)
                      )
                    }
                  />
                  <div className='flex min-w-0 flex-col gap-0.5'>
                    <FieldLabel htmlFor={id}>{info.name}</FieldLabel>
                    <Muted variant='caption'>{info.hint}</Muted>
                  </div>
                </li>
              )
            })}
          </ul>
          {limit !== undefined && (
            <Muted variant='caption'>{`Pick up to ${limit}.`}</Muted>
          )}
          <div className='flex min-w-0 flex-wrap gap-2'>
            <ActionButton
              label='Declare my passions'
              variant='default'
              blocked={
                reason() ??
                (chosen.length === 0
                  ? 'Pick at least one passion.'
                  : overLimit
                    ? `You can pick at most ${limit} passions.`
                    : null)
              }
              pending={declare.isPending}
              onRun={() =>
                declare.mutate({ passions: chosen, automatic: false })
              }
            />
            <ActionButton
              label='Read automatically'
              blocked={
                reason() ?? (reputation.automatic ? 'Already automatic.' : null)
              }
              pending={declare.isPending}
              onRun={() => declare.mutate({ passions: [], automatic: true })}
            />
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}
