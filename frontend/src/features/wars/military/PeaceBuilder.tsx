import { useState } from 'react'
import {
  Coins,
  Crown,
  Handshake,
  HeartHandshake,
  MapPin,
  Scale,
  ScrollText,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { EmptyState, EntityLink, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { EntityPicker } from './controls'
import { TERM, depthKeys, nameOf, termParamText, usePeaceTerms } from './depth'
import { type Named, busyOf } from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  Panel,
  Plain,
  Tag,
  NumberField,
  ToggleField,
} from './parts'
import { useNameMap } from './recordHooks'

type TermKind = components['schemas']['PeaceTermKind']
type Param = {
  key: string
  label: string
  icon: typeof Coins
  types?: string[]
}
const PARAM_TERMS: Record<string, Param[]> = {
  reparations: [{ key: 'amount', label: 'Reparations in wealth', icon: Coins }],
  tribute: [
    { key: 'amount', label: 'Tribute in wealth', icon: Coins },
    { key: 'epochs', label: 'Tribute for epochs', icon: Crown },
  ],
  demilitarised: [
    {
      key: 'region',
      label: 'Border left unguarded',
      icon: MapPin,
      types: ['region'],
    },
  ],
  cession: [
    { key: 'region', label: 'Land ceded', icon: MapPin, types: ['region'] },
  ],
  marriage: [
    {
      key: 'first_house',
      label: 'First house',
      icon: HeartHandshake,
      types: ['house'],
    },
    {
      key: 'second_house',
      label: 'Second house',
      icon: HeartHandshake,
      types: ['house'],
    },
  ],
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
  const [params, setParams] = useState<
    Record<string, Record<string, number | null>>
  >({})
  const names = useNameMap()
  const setParam = (kind: string, key: string, next: number | null) =>
    setParams((current) => ({
      ...current,
      [kind]: { ...current[kind], [key]: next },
    }))
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
                params: Object.fromEntries(
                  Object.entries(params[kind] ?? {}).filter(
                    (entry): entry is [string, number] => entry[1] !== null
                  )
                ),
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
          <Paged items={signed} as='li'>
            {(term) => (
              <li
                key={term.id}
                className='flex min-w-0 flex-wrap items-center gap-1.5 rounded-md border p-2'
              >
                <Tag item={nameOf(TERM, term.kind)} />
                {termParamText(term.kind, term.params, names) && (
                  <Text as='span' variant='caption' weight='medium'>
                    {termParamText(term.kind, term.params, names)}
                  </Text>
                )}
                {term.beneficiary && (
                  <Text as='span' variant='caption'>
                    for {term.beneficiary.name}
                  </Text>
                )}
                {typeof term.params.cost === 'number' && (
                  <Plain
                    icon={Scale}
                  >{`Cost ${term.params.cost} of war score`}</Plain>
                )}
                {term.params.separate === true && (
                  <Plain icon={Handshake}>Separate peace</Plain>
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
            )}
          </Paged>
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
        {Object.entries(PARAM_TERMS).some(([kind]) => chosen[kind]) && (
          <FieldGrid>
            {Object.entries(PARAM_TERMS)
              .filter(([kind]) => chosen[kind])
              .flatMap(([kind, fields]) =>
                fields.map((field) =>
                  field.types ? (
                    <EntityPicker
                      key={`${kind}.${field.key}`}
                      label={field.label}
                      icon={field.icon}
                      types={field.types}
                      value={params[kind]?.[field.key] ?? null}
                      onChange={(next) => setParam(kind, field.key, next)}
                      blocked={blocked}
                    />
                  ) : (
                    <NumberField
                      key={`${kind}.${field.key}`}
                      label={field.label}
                      icon={field.icon}
                      value={String(params[kind]?.[field.key] ?? '')}
                      onChange={(next) =>
                        setParam(
                          kind,
                          field.key,
                          next === ''
                            ? null
                            : Math.max(0, Math.round(Number(next) || 0))
                        )
                      }
                    />
                  )
                )
              )}
          </FieldGrid>
        )}
        <Button
          size='sm'
          className='self-start'
          disabled={busyOf(blocked, make.isPending) !== null}
          disabledReason={busyOf(blocked, make.isPending) ?? undefined}
          onClick={() => make.mutate()}
        >
          <Handshake />
          Make peace
        </Button>
      </Adjust>
    </Panel>
  )
}
