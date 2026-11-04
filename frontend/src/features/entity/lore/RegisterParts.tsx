import { useState } from 'react'
import { Lock, Trash2, Unlock } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodAction } from '@/features/pantheon/godAction'
import { ChoicePicker, NamedChip, RefChip } from './LoreFields'
import { REGISTERS, type RegisterKind } from './cultureLabels'
import { busyOf, lookup } from './model'

type RegisterView = components['schemas']['RegisterView']
const HOLDERS = ['settlement', 'people', 'cult', 'polity', 'faction'] as const

function useRegister() {
  return useGodAction<{
    holder: number
    kind: RegisterKind
    language: number | null
    hold: boolean
  }>({
    run: ({ holder, kind, language, hold }) =>
      unwrap(
        api.POST('/api/actions/language:register', {
          body: { holder_id: holder, kind, language_id: language, hold },
        })
      ),
  })
}

export function RegisterList({
  rows,
  surface,
  showLanguage = false,
}: {
  rows: readonly RegisterView[]
  surface: string
  showLanguage?: boolean
}) {
  if (rows.length === 0)
    return (
      <Muted data-surface={surface}>
        No court, faith, market or hearth speaks in it yet.
      </Muted>
    )
  return (
    <ul data-surface={surface} className='flex min-w-0 flex-col gap-2'>
      <Paged items={rows} as='li'>
        {(row) => {
          const spec = lookup(REGISTERS, row.kind)
          return (
            <li
              key={`${row.holder?.id}.${row.kind}`}
              className='flex min-w-0 flex-wrap items-center gap-2'
            >
              <NamedChip spec={spec}>{spec.label}</NamedChip>
              <RefChip icon={spec.icon} label='' item={row.holder} />
              {showLanguage && (
                <RefChip icon={spec.icon} label='in' item={row.language} />
              )}
              {row.held && (
                <Badge size='sm' variant='default'>
                  <Lock aria-hidden='true' />
                  Held
                </Badge>
              )}
              <Text as='span' variant='caption'>
                {`since epoch ${row.since_epoch}`}
              </Text>
            </li>
          )
        }}
      </Paged>
    </ul>
  )
}

export function RegisterEditor({
  languageId,
  rows,
  blocked,
}: {
  languageId: number
  rows: readonly RegisterView[]
  blocked: string | null
}) {
  const [holder, setHolder] = useState<number | null>(null)
  const [kind, setKind] = useState<RegisterKind>('court')
  const register = useRegister()
  const busy = busyOf(blocked, register.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {rows.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={rows} as='li'>
            {(row) => {
              const spec = lookup(REGISTERS, row.kind)
              const target = row.holder?.id ?? 0
              return (
                <li
                  key={`${target}.${row.kind}`}
                  className='flex min-w-0 flex-wrap items-center gap-2'
                >
                  <NamedChip spec={spec}>{spec.label}</NamedChip>
                  <Text as='span'>{row.holder?.name ?? 'Unknown'}</Text>
                  {row.held ? (
                    <Button
                      size='sm'
                      variant='outline'
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() =>
                        register.mutate({
                          holder: target,
                          kind: row.kind,
                          language: languageId,
                          hold: false,
                        })
                      }
                    >
                      <Unlock />
                      Let the world decide
                    </Button>
                  ) : (
                    <Button
                      size='sm'
                      variant='outline'
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() =>
                        register.mutate({
                          holder: target,
                          kind: row.kind,
                          language: languageId,
                          hold: true,
                        })
                      }
                    >
                      <Lock />
                      Hold it
                    </Button>
                  )}
                  <Button
                    size='icon'
                    variant='ghost'
                    aria-label={`Clear the ${spec.label} register of ${row.holder?.name ?? 'it'}`}
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() =>
                      register.mutate({
                        holder: target,
                        kind: row.kind,
                        language: null,
                        hold: false,
                      })
                    }
                  >
                    <Trash2 />
                  </Button>
                </li>
              )
            }}
          </Paged>
        </ul>
      )}
      <div className='grid min-w-0 grid-cols-1 items-end gap-3 md:grid-cols-3'>
        <EntityPicker
          types={HOLDERS}
          value={holder}
          onChange={setHolder}
          placeholder='Choose a court, faith or town…'
        />
        <ChoicePicker
          label='Register'
          value={kind}
          table={REGISTERS}
          blocked={busy}
          onPick={(next) => setKind(next as RegisterKind)}
        />
        <Button
          size='sm'
          disabled={busy !== null || holder === null}
          disabledReason={
            busy ?? (holder === null ? 'Choose who speaks it' : undefined)
          }
          onClick={() =>
            register.mutate({
              holder: holder ?? 0,
              kind,
              language: languageId,
              hold: true,
            })
          }
        >
          <Lock />
          Make it theirs and hold it
        </Button>
      </div>
    </div>
  )
}
