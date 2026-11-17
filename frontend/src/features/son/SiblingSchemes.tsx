import { useState } from 'react'
import { Ban, HandHeart } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { FormRow } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { type SonRecord, useSons } from '@/features/pantheon/api'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

type SchemeKind = components['schemas']['SchemeKind']

const SCHEMES: readonly { kind: SchemeKind; label: string; rule: string }[] = [
  { kind: 'rite', label: 'A rite', rule: 'death.sibling_rite_cost' },
  {
    kind: 'descent',
    label: 'Descent below',
    rule: 'death.sibling_descent_cost',
  },
  {
    kind: 'bargain',
    label: 'A foreign bargain',
    rule: 'death.sibling_bargain_cost',
  },
]

const SCHEME_TEXT: Record<SchemeKind, string> = {
  rite: 'A sure rite that adds devotion to their return.',
  descent:
    'They go down to the dead: much devotion if it works, a long sleep if it fails.',
  bargain:
    'They trade with an awake foreign god for devotion; one of the faithful pays.',
}

export function SiblingSchemes({ son }: { son: SonRecord }) {
  const sons = useSons()
  const rule = useRuleLookup()
  const { reason } = useGodGate()
  const [siblingId, setSiblingId] = useState<number | null>(null)
  const [kind, setKind] = useState<SchemeKind>('rite')
  const awake = (sons.data ?? [])
    .map((view) => view.son)
    .filter((item) => item.id !== son.id && item.status === 'active')
  const sibling = awake.find((item) => item.id === siblingId) ?? null
  const scheme = SCHEMES.find((item) => item.kind === kind) ?? SCHEMES[0]
  const schemeCost = rule(scheme.rule)
  const hinderCost = rule('death.hinder_return_cost')
  const hinderLoss = rule('death.hinder_return_devotion_loss')
  const plot = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/sons/{son_id}/scheme', {
          params: { path: { son_id: son.id } },
          body: { sibling_id: siblingId ?? 0, kind },
        })
      ),
  })
  const hinder = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/sons/{son_id}/hinder-return', {
          params: { path: { son_id: son.id } },
          body: { sibling_id: siblingId ?? 0 },
        })
      ),
  })
  const short = (cost: number | undefined) =>
    sibling && cost !== undefined && sibling.essence < cost
      ? `${sibling.name} has ${sibling.essence} essence; this needs ${cost}.`
      : null
  const blocked = reason() ?? (sibling ? null : 'Choose a sibling first.')
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Label variant='overline'>Their siblings</Label>
      {awake.length === 0 ? (
        <Muted>No sibling is awake to scheme for them or against them.</Muted>
      ) : (
        <>
          <FormRow label='Sibling' description='Pays from their own essence.'>
            {(id) => (
              <Select
                value={siblingId === null ? '' : String(siblingId)}
                onValueChange={(value) => setSiblingId(Number(value))}
              >
                <SelectTrigger id={id} className='w-full'>
                  <SelectValue placeholder='Choose a sibling' />
                </SelectTrigger>
                <SelectContent>
                  {awake.map((item) => (
                    <SelectItem key={item.id} value={String(item.id)}>
                      {`${item.name} · ${item.essence} essence`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </FormRow>
          <FormRow label='Scheme' description={SCHEME_TEXT[kind]}>
            {(id) => (
              <ToggleGroup
                id={id}
                type='single'
                variant='outline'
                value={kind}
                onValueChange={(value) => value && setKind(value as SchemeKind)}
              >
                {SCHEMES.map((item) => (
                  <ToggleGroupItem key={item.kind} value={item.kind}>
                    {item.label}
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            )}
          </FormRow>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <ActionButton
              label='Scheme for their return'
              icon={HandHeart}
              blocked={blocked ?? short(schemeCost)}
              pending={plot.isPending}
              onRun={() => plot.mutate()}
            />
            <ActionButton
              label='Hinder their return'
              icon={Ban}
              variant='destructive'
              blocked={blocked ?? short(hinderCost)}
              pending={hinder.isPending}
              confirm={{
                title: `Hinder the return of ${son.name}?`,
                description: `${sibling?.name ?? 'The sibling'} pays ${hinderCost ?? 'its'} essence; every resurrection cult loses ${hinderLoss ?? 'some'} devotion and becomes their enemy.`,
                confirmLabel: 'Hinder it',
              }}
              onRun={() => hinder.mutate()}
            />
          </div>
          {schemeCost !== undefined && (
            <Muted variant='caption'>{`This scheme costs the sibling ${schemeCost} essence.`}</Muted>
          )}
        </>
      )}
    </div>
  )
}
