import { useState } from 'react'
import { Handshake, ScrollText } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState, EntityLink } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { TERM, depthKeys, nameOf, usePeaceTerms } from './depth'
import { type Named, busyOf } from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  Panel,
  Tag,
  ToggleField,
} from './parts'

type TermKind = components['schemas']['PeaceTermKind']
const PARAM_TERMS: Record<string, string> = {
  reparations: 'amount',
  tribute: 'amount',
  demilitarised: 'region',
  cession: 'region',
  marriage: 'first_house',
}

export function PeaceTreaty({
  warId,
  sides,
  blocked,
}: {
  warId: number
  sides: { id: number; name: string }[]
  blocked: string | null
}) {
  const terms = usePeaceTerms(warId)
  const [victor, setVictor] = useState('white')
  const [chosen, setChosen] = useState<Record<string, boolean>>({
    captive_release: true,
  })
  const [params, setParams] = useState<Record<string, string>>({})
  const victors: Record<string, Named> = {
    white: { label: 'No victor: white peace', icon: Handshake, tone: 'muted' },
    ...Object.fromEntries(
      sides.map((side) => [
        String(side.id),
        { label: `${side.name} wins`, icon: Handshake, tone: 'gold' as const },
      ])
    ),
  }
  const make = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:peace', {
          body: {
            war_id: warId,
            victor_id: victor === 'white' ? null : Number(victor),
            terms: Object.entries(chosen)
              .filter(([, on]) => on)
              .map(([kind]) => ({
                kind: kind as TermKind,
                params:
                  PARAM_TERMS[kind] && params[kind]
                    ? { [PARAM_TERMS[kind]]: Number(params[kind]) }
                    : {},
              })),
          },
        })
      ),
    invalidate: [depthKeys.terms(warId) as unknown as unknown[], ['wars']],
  })
  const signed = terms.data ?? []
  return (
    <Panel
      title='Peace'
      icon={ScrollText}
      tone='verdigris'
      count={signed.length}
      hint='Every ending is written down as terms of a treaty'
    >
      {signed.length === 0 ? (
        <EmptyState
          icon={ScrollText}
          title='No peace terms yet'
          description='Set the victor, choose the clauses and make the peace.'
        />
      ) : (
        <ul className='flex min-w-0 flex-col gap-1.5'>
          {signed.map((term) => (
            <li
              key={term.id}
              className='flex min-w-0 flex-wrap items-center gap-1.5 rounded-md border p-2'
            >
              <Tag item={nameOf(TERM, term.kind)} />
              {term.beneficiary && (
                <Text as='span' variant='caption'>
                  for {term.beneficiary.name}
                </Text>
              )}
              {term.treaty && (
                <EntityLink kind='entity' id={String(term.treaty.id)}>
                  {term.treaty.name}
                </EntityLink>
              )}
              {term.note && (
                <Muted as='span' variant='caption' truncate>
                  {term.note}
                </Muted>
              )}
            </li>
          ))}
        </ul>
      )}
      <Adjust
        title='Peace builder'
        note='Pick who won and the clauses the treaty will carry; the aims each side achieved add their own terms.'
        label='Build a peace'
      >
        <FieldGrid>
          <ChoiceField
            label='Outcome'
            value={victor}
            table={victors}
            blocked={blocked}
            onPick={setVictor}
          />
        </FieldGrid>
        <FieldGrid>
          {Object.entries(TERM).map(([kind, item]) => (
            <ToggleField
              key={kind}
              item={item}
              checked={Boolean(chosen[kind])}
              disabled={blocked !== null}
              onChange={(next) =>
                setChosen((current) => ({ ...current, [kind]: next }))
              }
            />
          ))}
        </FieldGrid>
        {Object.entries(PARAM_TERMS)
          .filter(([kind]) => chosen[kind])
          .map(([kind, key]) => (
            <label key={kind} className='flex min-w-0 items-center gap-2'>
              <Text as='span' variant='caption' className='shrink-0'>
                {nameOf(TERM, kind).label}: {key.replaceAll('_', ' ')}
              </Text>
              <Input
                type='number'
                inputMode='numeric'
                value={params[kind] ?? ''}
                onChange={(event) =>
                  setParams((current) => ({
                    ...current,
                    [kind]: event.target.value,
                  }))
                }
              />
            </label>
          ))}
        <Button
          size='sm'
          className='self-start'
          disabled={busyOf(blocked, make.isPending) !== null}

          disabledReason={
            busyOf(blocked, make.isPending) !== null
              ? (blocked ?? 'Fill in what is needed first')
              : undefined
          }
          onClick={() => make.mutate()}
        >
          <Handshake />
          Make peace
        </Button>
      </Adjust>
    </Panel>
  )
}
