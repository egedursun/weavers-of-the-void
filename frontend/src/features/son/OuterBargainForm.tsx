import { useState } from 'react'
import { Ban, Eye, ShieldOff } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FormRow } from '@/components/domain'
import { Muted } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

type SonRecord = components['schemas']['SonRecord']
type Mode = components['schemas']['OuterBargainMode']

const OUTER_TYPES = ['outer_being'] as const
const TERMS_MAX = 200
const PER_EPOCH_RULE = 'son_tools.outer_bargain_per_epoch'
const DEFAULT_TERMS = "the Creator's command"

type OuterBargainFormProps = {
  sons: SonRecord[]
  fixedSonId?: number
}

export function OuterBargainForm({ sons, fixedSonId }: OuterBargainFormProps) {
  const living = sons.filter((son) => son.status !== 'dead')
  const [chosen, setChosen] = useState<number | null>(fixedSonId ?? null)
  const [outer, setOuter] = useState<number | null>(null)
  const [terms, setTerms] = useState('')
  const { reason } = useGodGate()
  const rule = useRuleLookup()
  const perEpoch = rule(PER_EPOCH_RULE)
  const sonId = fixedSonId ?? chosen
  const son = living.find((item) => item.id === sonId)
  const order = useGodAction({
    run: (mode: Mode) =>
      unwrap(
        api.POST('/api/actions/son:outer_bargain', {
          body: {
            son_id: sonId ?? 0,
            mode,
            outer_id: mode === 'force' ? outer : null,
            request: terms.trim() || DEFAULT_TERMS,
          },
        })
      ),
  })
  const noSon = son ? null : 'Choose a son first.'
  const forbidden = son?.outer_bargain_forbidden ?? false
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {fixedSonId === undefined && (
        <FormRow label='Son'>
          {(id) => (
            <Select
              value={sonId === null ? '' : String(sonId)}
              onValueChange={(value) => setChosen(Number(value))}
            >
              <SelectTrigger id={id} className='w-full'>
                <SelectValue placeholder='Choose a son' />
              </SelectTrigger>
              <SelectContent>
                {living.map((item) => (
                  <SelectItem key={item.id} value={String(item.id)}>
                    {item.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </FormRow>
      )}
      {son && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Badge size='sm' variant={forbidden ? 'destructive' : 'outline'}>
            {forbidden ? 'Forbidden to bargain' : 'Free to bargain'}
          </Badge>
          <Muted as='span' variant='caption'>
            {perEpoch === undefined
              ? 'They may bargain on their own when a thing outside stirs.'
              : `On their own they may bargain ${perEpoch} ${perEpoch === 1 ? 'time' : 'times'} an epoch when a thing outside stirs.`}
          </Muted>
        </div>
      )}
      <FormRow label='Outer being' description='Needed to force a bargain.'>
        {(id) => (
          <EntityPicker
            id={id}
            types={OUTER_TYPES}
            value={outer}
            onChange={setOuter}
            placeholder='Choose a thing from outside'
          />
        )}
      </FormRow>
      <FormRow label='What they ask for' description='Optional'>
        {(id) => (
          <Input
            id={id}
            value={terms}
            maxLength={TERMS_MAX}
            placeholder="The Creator's command"
            onChange={(event) => setTerms(event.target.value)}
          />
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <ActionButton
          label='Force the bargain'
          icon={Eye}
          variant='destructive'
          blocked={
            reason() ??
            noSon ??
            (outer === null ? 'Choose an outer being first.' : null)
          }
          pending={order.isPending && order.variables === 'force'}
          confirm={{
            title: `Make ${son?.name ?? 'them'} bargain with the outside?`,
            description:
              'They gain essence and ambition, lose loyalty, their siblings sour on them and the world leaks. The price is asked one day.',
            confirmLabel: 'Force it',
          }}
          onRun={() => order.mutate('force')}
        />
        {forbidden ? (
          <ActionButton
            label='Allow bargaining'
            icon={ShieldOff}
            blocked={reason() ?? noSon}
            pending={order.isPending && order.variables === 'allow'}
            onRun={() => order.mutate('allow')}
          />
        ) : (
          <ActionButton
            label='Forbid bargaining'
            icon={Ban}
            blocked={reason() ?? noSon}
            pending={order.isPending && order.variables === 'forbid'}
            onRun={() => order.mutate('forbid')}
          />
        )}
      </div>
    </div>
  )
}
