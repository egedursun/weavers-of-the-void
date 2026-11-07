import { useState } from 'react'
import { Eye, Plus, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { EmptyState, KpiTile, Paged, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type Belief,
  type BeliefSource,
  type Favour,
  type FavourOrigin,
  type Hook,
  type HookDemand,
  type HookStrength,
  type Intrigue,
  type IdentityReason,
  type Scheme,
  type PlotKind,
  type SchemePhase,
  type Secret,
  type IntrigueSecret,
  useIntrigue,
} from '../intrigue/api'
import {
  BELIEF_ICON,
  FAVOUR_ICON,
  HOOK_ICON,
  IDENTITY_ICON,
  INTRIGUE_ICON,
  NAME_ICON,
  OPEN_PHASES,
  PHASES,
  SCHEME_ICON,
  SECRET_ICON,
  WITNESS_ICON,
  severityTone,
} from '../intrigue/labels'
import {
  AddBar,
  ControlPanel,
  ItemRow,
  MindCard,
  MindPicker,
  NodePicker,
} from '../mind/parts'
import { NodeListEditor, RefLink } from '../realm/parts'

const SPAN = 100
const WORKING = 'Working on it.'
const BEINGS = [
  'mortal',
  'settlement',
  'people',
  'polity',
  'house',
  'faction',
  'cult',
  'spirit',
  'outer_being',
  'creature',
  'place',
  'item',
]
const STRENGTHS: Record<string, string> = { weak: 'Weak', strong: 'Strong' }
const STRENGTH_RANK: Record<string, string> = {
  weak: 'Spent once used',
  strong: 'Lasts through every use',
}

type Ctx = {
  view: Intrigue
  blocked: string | null
  hold: boolean
}

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function table(
  items: { key: string; label: string }[]
): Record<string, string> {
  return Object.fromEntries(items.map((item) => [item.key, item.label]))
}

function Ref({
  node,
}: {
  node: { id: number; kind: string; name: string } | null
}) {
  if (!node) return <span>someone now gone</span>
  return <RefLink node={node} />
}

function Held({ held }: { held: boolean }) {
  return held ? <Badge variant='outline'>Held</Badge> : null
}

function SecretRow({
  secret,
  ctx,
  own,
}: {
  secret: Secret
  ctx: Ctx
  own: boolean
}) {
  const reveal = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/secret:expose', {
          body: { secret_id: secret.id },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/secret:delete', {
          body: { secret_id: secret.id },
        })
      ),
  })
  const freeze = useGodAction({
    run: (hold: boolean) =>
      unwrap(
        api.POST('/api/actions/secret:hold', {
          body: { secret_id: secret.id, hold },
        })
      ),
  })
  const busy = why(
    ctx.blocked,
    reveal.isPending,
    strike.isPending,
    freeze.isPending
  )
  const out = secret.exposed_epoch !== null
  const frozen = secret.held.length > 0
  return (
    <ItemRow
      icon={out ? WITNESS_ICON : SECRET_ICON}
      tone={out ? 'muted' : severityTone(secret.severity)}
      title={
        own ? (
          secret.label
        ) : (
          <>
            {`${secret.label} of `}
            <Ref node={secret.holder} />
          </>
        )
      }
      meta={
        <>
          {secret.about && (
            <>
              {'Concerning '}
              <Ref node={secret.about} />
              {', '}
            </>
          )}
          {`weight ${secret.severity}, known to ${secret.known_by.length}`}
          {out
            ? `, out since epoch ${secret.exposed_epoch}`
            : `, kept since epoch ${secret.created_epoch}`}
        </>
      }
      badges={
        <>
          {out && <Badge variant='destructive'>Exposed</Badge>}
          <Held held={frozen} />
        </>
      }
      actions={
        <>
          {!out && (
            <Button
              size='icon-sm'
              variant='ghost'
              aria-label={`Expose ${secret.label.toLowerCase()}`}
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => reveal.mutate()}
            >
              <Eye />
            </Button>
          )}
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label={`Strike ${secret.label.toLowerCase()}`}
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strike.mutate()}
          >
            <X />
          </Button>
        </>
      }
      editLabel={secret.label.toLowerCase()}
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <AdjustStats
            id={`secret-${secret.id}`}
            inline
            groups={[
              {
                title: 'Secret',
                fields: [
                  {
                    key: 'severity',
                    label: 'Weight',
                    value: secret.severity,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ value }) =>
              unwrap(
                api.POST('/api/actions/secret:edit', {
                  body: {
                    secret_id: secret.id,
                    severity: value,
                    hold: ctx.hold,
                  },
                })
              )
            }
          />
          <Muted variant='caption'>
            {secret.known_by.length > 0
              ? `Known to ${secret.known_by.map((node) => node.name).join(', ')}.`
              : 'Known to no one.'}
          </Muted>
          <div className='flex justify-end'>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => freeze.mutate(!frozen)}
            >
              {frozen ? 'Let it move again' : 'Hold it as it stands'}
            </Button>
          </div>
        </div>
      }
    />
  )
}

function SecretsCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const [kind, setKind] = useState('')
  const keep = useGodAction({
    run: (value: IntrigueSecret) =>
      unwrap(
        api.POST('/api/actions/secret:keep', {
          body: { holder_id: view.node_id, kind: value, known_by: [] },
        })
      ),
    success: () => {
      setKind('')
      return 'Secret kept'
    },
  })
  const busy = why(ctx.blocked, keep.isPending)
  return (
    <MindCard
      title='Secrets'
      icon={SECRET_ICON}
      wide
      hint='Whoever learns a secret holds a hook on its keeper; a weighty one gives a strong hook. When a secret comes out its keeper is shamed and judged by the ethics of the people.'
    >
      {view.secrets.length === 0 ? (
        <Muted variant='caption'>Keeps no secret of its own.</Muted>
      ) : (
        <Paged items={view.secrets} initial={4} noun={['secret', 'secrets']}>
          {(secret) => (
            <SecretRow key={secret.id} secret={secret} ctx={ctx} own />
          )}
        </Paged>
      )}
      {view.known_secrets.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Secrets it knows of others</Label>
          <Paged
            items={view.known_secrets}
            initial={3}
            noun={['secret', 'secrets']}
          >
            {(secret) => (
              <SecretRow
                key={secret.id}
                secret={secret}
                ctx={ctx}
                own={false}
              />
            )}
          </Paged>
        </div>
      )}
      <AddBar
        title='Give it a secret'
        action={
          <Button
            size='sm'
            disabled={busy !== null || !kind}
            disabledReason={busy ?? (kind ? undefined : 'Choose a kind first.')}
            onClick={() => keep.mutate(kind as IntrigueSecret)}
          >
            <Plus />
            Keep it
          </Button>
        }
      >
        <MindPicker
          label='Kind of secret'
          value={kind}
          table={table(view.secret_kinds)}
          blocked={busy}
          onPick={setKind}
        />
      </AddBar>
    </MindCard>
  )
}

function HookRow({ hook, ctx, held }: { hook: Hook; ctx: Ctx; held: boolean }) {
  const [demand, setDemand] = useState('')
  const use = useGodAction({
    run: (value: HookDemand) =>
      unwrap(
        api.POST('/api/actions/hook:use', {
          body: { hook_id: hook.id, demand: value },
        })
      ),
  })
  const edit = useGodAction({
    run: (value: HookStrength) =>
      unwrap(
        api.POST('/api/actions/hook:edit', {
          body: {
            hook_id: hook.id,
            strength: value,
            clear_demand: false,
            hold: ctx.hold,
          },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/hook:delete', { body: { hook_id: hook.id } })
      ),
  })
  const recall = useGodAction({
    run: (value: HookDemand | null) =>
      unwrap(
        api.POST('/api/actions/hook:edit', {
          body: {
            hook_id: hook.id,
            last_demand: value,
            clear_demand: value === null,
            hold: ctx.hold,
          },
        })
      ),
  })
  const demands = table(ctx.view.hook_demands)
  const busy = why(
    ctx.blocked,
    use.isPending,
    edit.isPending,
    strike.isPending,
    recall.isPending
  )
  const spent = hook.used_epoch !== null
  const other = held ? hook.target : hook.holder
  return (
    <ItemRow
      icon={HOOK_ICON}
      tone={spent ? 'muted' : hook.strength === 'strong' ? 'danger' : 'warning'}
      title={
        <>
          {held ? 'On ' : 'Held by '}
          <Ref node={other} />
        </>
      }
      meta={`${STRENGTHS[hook.strength]} hook from ${hook.source_label.toLowerCase()}; ${spent ? `spent in epoch ${hook.used_epoch}` : STRENGTH_RANK[hook.strength].toLowerCase()}${hook.last_demand ? `; last pressed for ${(demands[hook.last_demand] ?? hook.last_demand).toLowerCase()}` : ''}`}
      badges={<Held held={hook.held} />}
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Break the hook'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the hook'
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <MindPicker
            label='Strength'
            value={hook.strength}
            table={STRENGTHS}
            blocked={busy}
            onPick={(value) => edit.mutate(value as HookStrength)}
          />
          <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-2'>
            <MindPicker
              label='Last demand'
              value={hook.last_demand ?? ''}
              table={demands}
              blocked={busy}
              onPick={(value) => recall.mutate(value as HookDemand)}
            />
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || !hook.last_demand}
              disabledReason={
                busy ?? (hook.last_demand ? undefined : 'No demand to forget.')
              }
              onClick={() => recall.mutate(null)}
            >
              Forget the demand
            </Button>
          </div>
          {!spent && (
            <AddBar
              title='Press it'
              action={
                <Button
                  size='sm'
                  disabled={busy !== null || !demand}
                  disabledReason={
                    busy ?? (demand ? undefined : 'Choose a demand first.')
                  }
                  onClick={() => use.mutate(demand as HookDemand)}
                >
                  Press
                </Button>
              }
            >
              <MindPicker
                label='Demand'
                value={demand}
                table={table(ctx.view.hook_demands)}
                blocked={busy}
                onPick={setDemand}
              />
            </AddBar>
          )}
        </div>
      }
    />
  )
}

function HooksCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const [target, setTarget] = useState<number | null>(null)
  const [strength, setStrength] = useState('weak')
  const grant = useGodAction({
    run: (targetId: number) =>
      unwrap(
        api.POST('/api/actions/hook:grant', {
          body: {
            holder_id: view.node_id,
            target_id: targetId,
            strength: strength as HookStrength,
            source: 'secret',
          },
        })
      ),
    success: () => {
      setTarget(null)
      return 'Hook granted'
    },
  })
  const busy = why(ctx.blocked, grant.isPending)
  const empty = view.hooks_held.length === 0 && view.hooks_on.length === 0
  return (
    <MindCard
      title='Hooks'
      icon={HOOK_ICON}
      hint='A hook forces its target to comply: to agree to a marriage, step down from office or lend support. A weak hook is spent on use; a strong one lasts.'
    >
      {empty && (
        <Muted variant='caption'>Holds no hook and is held by none.</Muted>
      )}
      {view.hooks_held.length > 0 && (
        <Paged items={view.hooks_held} initial={3} noun={['hook', 'hooks']}>
          {(hook) => <HookRow key={hook.id} hook={hook} ctx={ctx} held />}
        </Paged>
      )}
      {view.hooks_on.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Hooks others hold on it</Label>
          <Paged items={view.hooks_on} initial={3} noun={['hook', 'hooks']}>
            {(hook) => (
              <HookRow key={hook.id} hook={hook} ctx={ctx} held={false} />
            )}
          </Paged>
        </div>
      )}
      <AddBar
        title='Give it a hook'
        action={
          <Button
            size='sm'
            disabled={busy !== null || target === null}
            disabledReason={
              busy ?? (target === null ? 'Choose a target first.' : undefined)
            }
            onClick={() => target !== null && grant.mutate(target)}
          >
            <Plus />
            Grant
          </Button>
        }
      >
        <NodePicker
          label='Target'
          types={BEINGS}
          value={target}
          onChange={setTarget}
          blocked={busy}
        />
        <MindPicker
          label='Strength'
          value={strength}
          table={STRENGTHS}
          blocked={busy}
          onPick={setStrength}
        />
      </AddBar>
    </MindCard>
  )
}

function FavourRow({
  favour,
  ctx,
  owed,
}: {
  favour: Favour
  ctx: Ctx
  owed: boolean
}) {
  const call = useGodAction({
    run: (honour: boolean) =>
      unwrap(
        api.POST('/api/actions/favour:call', {
          body: { favour_id: favour.id, honour },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/favour:delete', {
          body: { favour_id: favour.id },
        })
      ),
  })
  const busy = why(ctx.blocked, call.isPending, strike.isPending)
  const called = favour.called_epoch !== null
  return (
    <ItemRow
      icon={FAVOUR_ICON}
      tone={called ? (favour.honoured ? 'success' : 'danger') : 'gold'}
      title={
        <>
          {owed ? 'Owes ' : 'Owed by '}
          <Ref node={owed ? favour.owed_to : favour.owed_by} />
        </>
      }
      meta={`${favour.origin_label}, weight ${favour.magnitude}${called ? `, ${favour.honoured ? 'honoured' : 'refused'} in epoch ${favour.called_epoch}` : `, since epoch ${favour.created_epoch}`}`}
      badges={<Held held={favour.held} />}
      actions={
        <>
          {!called && (
            <>
              <Button
                size='sm'
                variant='ghost'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => call.mutate(true)}
              >
                Honour
              </Button>
              <Button
                size='sm'
                variant='ghost'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => call.mutate(false)}
              >
                Refuse
              </Button>
            </>
          )}
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Forgive the favour'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strike.mutate()}
          >
            <X />
          </Button>
        </>
      }
      editLabel='the favour'
      editor={
        <AdjustStats
          id={`favour-${favour.id}`}
          inline
          groups={[
            {
              title: 'Favour',
              fields: [
                {
                  key: 'magnitude',
                  label: 'Weight',
                  value: favour.magnitude,
                  min: 1,
                  max: SPAN,
                },
              ],
            },
          ]}
          run={({ value }) =>
            unwrap(
              api.POST('/api/actions/favour:edit', {
                body: {
                  favour_id: favour.id,
                  magnitude: value,
                  hold: ctx.hold,
                },
              })
            )
          }
        />
      }
    />
  )
}

function FavoursCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const [creditor, setCreditor] = useState<number | null>(null)
  const [origin, setOrigin] = useState('gift')
  const owe = useGodAction({
    run: (creditorId: number) =>
      unwrap(
        api.POST('/api/actions/favour:owe', {
          body: {
            owed_by_id: view.node_id,
            owed_to_id: creditorId,
            magnitude: 20,
            origin: origin as FavourOrigin,
          },
        })
      ),
    success: () => {
      setCreditor(null)
      return 'Favour owed'
    },
  })
  const busy = why(ctx.blocked, owe.isPending)
  const empty = view.favours_owed.length === 0 && view.favours_due.length === 0
  return (
    <MindCard
      title='Favours'
      icon={FAVOUR_ICON}
      hint='Gifts, rescues, support in war or succession and help in a scheme leave favours owed. Honouring one wins trust; refusing a called favour costs trust and honour.'
    >
      {empty && (
        <Muted variant='caption'>Owes nothing and is owed nothing.</Muted>
      )}
      {view.favours_owed.length > 0 && (
        <Paged
          items={view.favours_owed}
          initial={3}
          noun={['favour', 'favours']}
        >
          {(favour) => (
            <FavourRow key={favour.id} favour={favour} ctx={ctx} owed />
          )}
        </Paged>
      )}
      {view.favours_due.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Favours owed to it</Label>
          <Paged
            items={view.favours_due}
            initial={3}
            noun={['favour', 'favours']}
          >
            {(favour) => (
              <FavourRow
                key={favour.id}
                favour={favour}
                ctx={ctx}
                owed={false}
              />
            )}
          </Paged>
        </div>
      )}
      <AddBar
        title='Put it in someone’s debt'
        action={
          <Button
            size='sm'
            disabled={busy !== null || creditor === null}
            disabledReason={
              busy ??
              (creditor === null ? 'Choose a creditor first.' : undefined)
            }
            onClick={() => creditor !== null && owe.mutate(creditor)}
          >
            <Plus />
            Owe
          </Button>
        }
      >
        <NodePicker
          label='Owed to'
          types={BEINGS}
          value={creditor}
          onChange={setCreditor}
          blocked={busy}
        />
        <MindPicker
          label='For'
          value={origin}
          table={table(view.favour_origins)}
          blocked={busy}
          onPick={setOrigin}
        />
      </AddBar>
    </MindCard>
  )
}

function IdentityCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const identity = view.identity
  const [name, setName] = useState('')
  const [reason, setReason] = useState('exile')
  const assume = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/identity:assume', {
          body: {
            mortal_id: view.node_id,
            false_name: name.trim(),
            reason: reason as IdentityReason,
          },
        })
      ),
    success: () => {
      setName('')
      return 'A new name is worn'
    },
  })
  const rename = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/identity:edit', {
          body: {
            mortal_id: view.node_id,
            false_name: name.trim(),
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setName('')
      return 'Renamed'
    },
  })
  const unmask = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/identity:unmask', {
          body: { mortal_id: view.node_id },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/identity:delete', {
          body: { mortal_id: view.node_id },
        })
      ),
  })
  const busy = why(
    ctx.blocked,
    assume.isPending,
    rename.isPending,
    unmask.isPending,
    strike.isPending
  )
  if (!view.can_hold_identity)
    return (
      <MindCard title='False identity' icon={IDENTITY_ICON}>
        <Muted variant='caption'>{view.identity_reason}</Muted>
      </MindCard>
    )
  const nameField = (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label as='label' htmlFor={`false-name-${view.node_id}`}>
        False name
      </Label>
      <Input
        id={`false-name-${view.node_id}`}
        value={name}
        maxLength={200}
        disabled={busy !== null}
        onChange={(event) => setName(event.target.value)}
      />
    </div>
  )
  return (
    <MindCard
      title='False identity'
      icon={IDENTITY_ICON}
      hint='Spies, the blood-cursed, exiles and impostors live under false names. Carelessness and a face others remember wear the mask thin; at full exposure it falls.'
    >
      {identity ? (
        <>
          <ItemRow
            icon={IDENTITY_ICON}
            tone={identity.exposed_epoch !== null ? 'muted' : 'verdigris'}
            title={`Lives as ${identity.false_name}`}
            meta={
              <>
                {identity.reason_label}
                {identity.cover_role
                  ? `, posing as a ${identity.cover_role}`
                  : ''}
                {identity.community && (
                  <>
                    {' in '}
                    <Ref node={identity.community} />
                  </>
                )}
              </>
            }
            badges={
              <>
                {identity.exposed_epoch !== null && (
                  <Badge variant='destructive'>Unmasked</Badge>
                )}
                <Held held={identity.held.length > 0} />
              </>
            }
            actions={
              <Button
                size='icon-sm'
                variant='ghost'
                aria-label='Strike the false name'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => strike.mutate()}
              >
                <X />
              </Button>
            }
            editLabel='the false identity'
            editor={
              <AdjustStats
                id={`identity-${view.node_id}`}
                inline
                groups={[
                  {
                    title: 'Mask',
                    fields: [
                      {
                        key: 'exposure',
                        label: 'Exposure',
                        value: identity.exposure,
                        min: 0,
                        max: SPAN,
                      },
                    ],
                  },
                ]}
                run={({ value }) =>
                  unwrap(
                    api.POST('/api/actions/identity:edit', {
                      body: {
                        mortal_id: view.node_id,
                        exposure: value,
                        hold: ctx.hold,
                      },
                    })
                  )
                }
              />
            }
          />
          <div className='flex min-w-0 flex-col gap-1'>
            <Muted variant='caption'>{`${identity.exposure}% seen through`}</Muted>
            <Progress
              value={identity.exposure}
              size='sm'
              tone={identity.exposure >= 70 ? 'warning' : 'success'}
              aria-label={`Exposure ${identity.exposure}`}
            />
          </div>
          <AddBar
            title='Change the mask'
            action={
              <div className='flex flex-wrap justify-end gap-2'>
                <Button
                  size='sm'
                  disabled={busy !== null || !name.trim()}
                  disabledReason={
                    busy ?? (name.trim() ? undefined : 'Write a name first.')
                  }
                  onClick={() => rename.mutate()}
                >
                  Rename
                </Button>
                {identity.exposed_epoch === null && (
                  <Button
                    size='sm'
                    variant='outline'
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => unmask.mutate()}
                  >
                    Unmask
                  </Button>
                )}
              </div>
            }
          >
            {nameField}
          </AddBar>
        </>
      ) : (
        <>
          <Text>Lives under their own name.</Text>
          <AddBar
            title='Give them a false name'
            action={
              <Button
                size='sm'
                disabled={busy !== null || !name.trim()}
                disabledReason={
                  busy ?? (name.trim() ? undefined : 'Write a name first.')
                }
                onClick={() => assume.mutate()}
              >
                <Plus />
                Wear it
              </Button>
            }
          >
            {nameField}
            <MindPicker
              label='Why'
              value={reason}
              table={table(view.identity_reasons)}
              blocked={busy}
              onPick={setReason}
            />
          </AddBar>
        </>
      )}
    </MindCard>
  )
}

function SchemeRow({ scheme, ctx }: { scheme: Scheme; ctx: Ctx }) {
  const phase = useGodAction({
    run: (value: SchemePhase) =>
      unwrap(
        api.POST('/api/actions/scheme:edit', {
          body: { scheme_id: scheme.id, phase: value, hold: ctx.hold },
        })
      ),
  })
  const crew = useGodAction({
    run: (body: { agents?: number[]; discovered_by?: number[] }) =>
      unwrap(
        api.POST('/api/actions/scheme:edit', {
          body: { scheme_id: scheme.id, ...body, hold: ctx.hold },
        })
      ),
  })
  const freeze = useGodAction({
    run: (hold: boolean) =>
      unwrap(
        api.POST('/api/actions/scheme:hold', {
          body: { scheme_id: scheme.id, hold },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/scheme:delete', {
          body: { scheme_id: scheme.id },
        })
      ),
  })
  const busy = why(
    ctx.blocked,
    phase.isPending,
    crew.isPending,
    freeze.isPending,
    strike.isPending
  )
  const look = PHASES[scheme.phase] ?? PHASES.recruit
  const frozen = scheme.held.length > 0
  return (
    <ItemRow
      icon={look.icon}
      tone={look.tone}
      title={
        <>
          {`${scheme.label} by `}
          <Ref node={scheme.owner} />
        </>
      }
      meta={
        <>
          {scheme.target && (
            <>
              {'Against '}
              <Ref node={scheme.target} />
              {', '}
            </>
          )}
          {`${scheme.phase_label.toLowerCase()}, power ${scheme.power} of ${scheme.difficulty}, secrecy ${scheme.secrecy}, ${scheme.agents.length} agents`}
          {scheme.outcome ? `: ${scheme.outcome}` : ''}
          {scheme.discovered_by.length > 0 &&
            `; discovered by ${scheme.discovered_by.map((node) => node.name).join(', ')}`}
        </>
      }
      badges={<Held held={frozen} />}
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Erase the ${scheme.label.toLowerCase()}`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel={scheme.label.toLowerCase()}
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <MindPicker
            label='Phase'
            value={scheme.phase}
            table={table(ctx.view.scheme_phases)}
            blocked={busy}
            onPick={(value) => phase.mutate(value as SchemePhase)}
          />
          <AdjustStats
            id={`scheme-${scheme.id}`}
            inline
            groups={[
              {
                title: 'Scheme',
                fields: [
                  { key: 'power', label: 'Power', value: scheme.power, min: 0 },
                  {
                    key: 'secrecy',
                    label: 'Secrecy',
                    value: scheme.secrecy,
                    min: 0,
                    max: SPAN,
                  },
                  {
                    key: 'progress',
                    label: 'Progress',
                    value: scheme.progress,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ key, value }) =>
              unwrap(
                api.POST('/api/actions/scheme:edit', {
                  body: { scheme_id: scheme.id, [key]: value, hold: ctx.hold },
                })
              )
            }
          />
          <NodeListEditor
            label='Agents'
            types={['mortal']}
            nodes={scheme.agents}
            blocked={busy}
            onChange={(ids) => crew.mutate({ agents: ids })}
          />
          <NodeListEditor
            label='Discovered by'
            types={['mortal', 'settlement', 'polity', 'people', 'faction']}
            nodes={scheme.discovered_by}
            blocked={busy}
            onChange={(ids) => crew.mutate({ discovered_by: ids })}
          />
          <div className='flex justify-end'>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => freeze.mutate(!frozen)}
            >
              {frozen ? 'Let it move again' : 'Freeze it where it stands'}
            </Button>
          </div>
        </div>
      }
    >
      {OPEN_PHASES.has(scheme.phase) && (
        <Progress
          value={scheme.progress}
          size='sm'
          tone='warning'
          aria-label={`Progress ${scheme.progress}`}
        />
      )}
    </ItemRow>
  )
}

function SchemesCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const [kind, setKind] = useState('')
  const [target, setTarget] = useState<number | null>(null)
  const begin = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/scheme:begin', {
          body: {
            owner_id: view.node_id,
            kind: kind as PlotKind,
            target_id: target,
          },
        })
      ),
    success: () => {
      setKind('')
      setTarget(null)
      return 'Scheme begun'
    },
  })
  const busy = why(ctx.blocked, begin.isPending)
  const empty = view.schemes.length === 0 && view.schemes_against.length === 0
  return (
    <MindCard
      title='Schemes'
      icon={SCHEME_ICON}
      wide
      hint='A scheme recruits agents, gathers power from their skill in intrigue and deception, then strikes against the target’s spymaster and intuition. Fog, storms, festivals, plague and siege change its odds; each epoch it may be discovered.'
    >
      {empty && <Muted variant='caption'>No scheme by or against it.</Muted>}
      {view.schemes.length > 0 && (
        <Paged items={view.schemes} initial={3} noun={['scheme', 'schemes']}>
          {(scheme) => <SchemeRow key={scheme.id} scheme={scheme} ctx={ctx} />}
        </Paged>
      )}
      {view.schemes_against.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Schemes against it</Label>
          <Paged
            items={view.schemes_against}
            initial={3}
            noun={['scheme', 'schemes']}
          >
            {(scheme) => (
              <SchemeRow key={scheme.id} scheme={scheme} ctx={ctx} />
            )}
          </Paged>
        </div>
      )}
      {view.can_scheme ? (
        <AddBar
          title='Set it plotting'
          action={
            <Button
              size='sm'
              disabled={busy !== null || !kind}
              disabledReason={
                busy ?? (kind ? undefined : 'Choose a scheme first.')
              }
              onClick={() => begin.mutate()}
            >
              <Plus />
              Begin
            </Button>
          }
        >
          <MindPicker
            label='Scheme'
            value={kind}
            table={table(view.scheme_kinds)}
            blocked={busy}
            onPick={setKind}
          />
          <NodePicker
            label='Target'
            types={BEINGS}
            value={target}
            onChange={setTarget}
            blocked={busy}
          />
        </AddBar>
      ) : (
        <Muted variant='caption'>{view.scheme_reason}</Muted>
      )}
    </MindCard>
  )
}

function TrueNameCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const known = view.true_name
  const [name, setName] = useState('')
  const [learner, setLearner] = useState<number | null>(null)
  const set = useGodAction({
    run: (value: string | null) =>
      unwrap(
        api.POST('/api/actions/true_name:set', {
          body: { bearer_id: view.node_id, name: value, hold: ctx.hold },
        })
      ),
    success: () => {
      setName('')
      return 'Named'
    },
  })
  const teach = useGodAction({
    run: ({ id, forget }: { id: number; forget: boolean }) =>
      unwrap(
        api.POST('/api/actions/true_name:teach', {
          body: { bearer_id: view.node_id, learner_id: id, forget },
        })
      ),
    success: () => {
      setLearner(null)
      return 'Done'
    },
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/true_name:delete', {
          body: { bearer_id: view.node_id },
        })
      ),
  })
  const busy = why(
    ctx.blocked,
    set.isPending,
    teach.isPending,
    strike.isPending
  )
  return (
    <MindCard
      title='True name'
      icon={NAME_ICON}
      hint='Knowing a true name gives a strong hook on its bearer, strengthens rites cast against it and shields from its own. Scholars of old tongues, schemes and divine revelation uncover them; a widely known name is cast off through rebirth or initiation.'
    >
      {known ? (
        <>
          <ItemRow
            icon={NAME_ICON}
            tone='gold'
            title={known.name}
            meta={`${known.language ? `In ${known.language.name}, ` : ''}borne since epoch ${known.since_epoch}, known to ${known.known_by.length}`}
            badges={<Held held={known.held.length > 0} />}
            actions={
              <Button
                size='icon-sm'
                variant='ghost'
                aria-label='Strike the true name'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => strike.mutate()}
              >
                <X />
              </Button>
            }
          />
          <Paged
            items={known.known_by}
            initial={4}
            noun={['knower', 'knowers']}
          >
            {(node) => (
              <div
                key={node.id}
                className='flex min-w-0 items-center justify-between gap-2'
              >
                <Text truncate>
                  <Ref node={node} />
                </Text>
                {node.id !== view.node_id && (
                  <Button
                    size='sm'
                    variant='ghost'
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => teach.mutate({ id: node.id, forget: true })}
                  >
                    Make them forget
                  </Button>
                )}
              </div>
            )}
          </Paged>
          <AddBar
            title='Reveal it'
            action={
              <Button
                size='sm'
                disabled={busy !== null || learner === null}
                disabledReason={
                  busy ??
                  (learner === null ? 'Choose who learns it.' : undefined)
                }
                onClick={() =>
                  learner !== null &&
                  teach.mutate({ id: learner, forget: false })
                }
              >
                Reveal
              </Button>
            }
          >
            <NodePicker
              label='Who learns it'
              types={BEINGS}
              value={learner}
              onChange={setLearner}
              blocked={busy}
            />
          </AddBar>
        </>
      ) : (
        <Muted variant='caption'>Carries no true name.</Muted>
      )}
      <AddBar
        title={known ? 'Change the true name' : 'Give it a true name'}
        action={
          <div className='flex flex-wrap justify-end gap-2'>
            <Button
              size='sm'
              disabled={busy !== null || !name.trim()}
              disabledReason={
                busy ?? (name.trim() ? undefined : 'Write a name first.')
              }
              onClick={() => set.mutate(name.trim())}
            >
              <Plus />
              Name it
            </Button>
            {known && (
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => set.mutate(null)}
              >
                Draw a new one
              </Button>
            )}
          </div>
        }
      >
        <div className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor={`true-name-${view.node_id}`}>
            True name
          </Label>
          <Input
            id={`true-name-${view.node_id}`}
            value={name}
            maxLength={200}
            disabled={busy !== null}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
      </AddBar>
      {view.names_known.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>True names it knows</Label>
          <Paged items={view.names_known} initial={4} noun={['name', 'names']}>
            {(entry) => (
              <ItemRow
                key={entry.bearer.id}
                icon={NAME_ICON}
                tone='verdigris'
                title={entry.name}
                meta={
                  <>
                    {'The true name of '}
                    <Ref node={entry.bearer} />
                  </>
                }
              />
            )}
          </Paged>
        </div>
      )}
    </MindCard>
  )
}

function BeliefRow({ belief, ctx }: { belief: Belief; ctx: Ctx }) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/belief:delete', {
          body: { belief_id: belief.id },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  const gap = belief.truth === null ? null : belief.value - belief.truth
  return (
    <ItemRow
      icon={BELIEF_ICON}
      tone={
        belief.false ? 'danger' : belief.confidence >= 60 ? 'info' : 'muted'
      }
      title={
        <>
          {`${belief.attribute_label} of `}
          <Ref node={belief.subject} />
          {`: ${belief.value}`}
        </>
      }
      meta={`${belief.source_label}, ${belief.confidence}% sure, as of epoch ${belief.as_of_epoch}${gap === null ? '' : gap === 0 ? ', true to the world' : `, ${Math.abs(gap)} ${gap > 0 ? 'above' : 'below'} the truth`}`}
      badges={
        <>
          {belief.false && <Badge variant='destructive'>Planted lie</Badge>}
          <Held held={belief.held.length > 0} />
        </>
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Wipe the belief'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the belief'
      editor={
        <AdjustStats
          id={`belief-${belief.id}`}
          inline
          groups={[
            {
              title: 'Belief',
              fields: [
                {
                  key: 'value',
                  label: 'Believed value',
                  value: belief.value,
                  min: 0,
                },
                {
                  key: 'confidence',
                  label: 'Confidence',
                  value: belief.confidence,
                  min: 0,
                  max: SPAN,
                },
              ],
            },
          ]}
          run={({ key, value }) =>
            unwrap(
              api.POST('/api/actions/belief:set', {
                body: {
                  holder_id: ctx.view.node_id,
                  subject_id: belief.subject?.id ?? 0,
                  attribute: belief.attribute,
                  value: key === 'value' ? value : belief.value,
                  confidence: key === 'confidence' ? value : belief.confidence,
                  source: belief.source,
                  false: belief.false,
                  hold: ctx.hold,
                },
              })
            )
          }
        />
      }
    />
  )
}

function BeliefsCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const [subject, setSubject] = useState<number | null>(null)
  const [attribute, setAttribute] = useState('')
  const [source, setSource] = useState('observation')
  const [value, setValue] = useState(50)
  const set = useGodAction({
    run: (subjectId: number) =>
      unwrap(
        api.POST('/api/actions/belief:set', {
          body: {
            holder_id: view.node_id,
            subject_id: subjectId,
            attribute,
            value,
            confidence: 80,
            source: source as BeliefSource,
            false: source === 'deception',
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setSubject(null)
      return 'Belief set'
    },
  })
  const busy = why(ctx.blocked, set.isPending)
  return (
    <MindCard
      title='What it believes'
      icon={BELIEF_ICON}
      wide
      hint='Decisions read beliefs, not the truth: raiders weigh the wealth they believe a neighbour holds, guarantors the defences they believe they face. Sight, spies, rumour and planted lies feed beliefs; confidence fades each epoch.'
    >
      {view.beliefs.length === 0 ? (
        <Muted variant='caption'>
          Believes nothing of others beyond a guess at the truth.
        </Muted>
      ) : (
        <Paged items={view.beliefs} initial={5} noun={['belief', 'beliefs']}>
          {(belief) => <BeliefRow key={belief.id} belief={belief} ctx={ctx} />}
        </Paged>
      )}
      <AddBar
        title='Put a belief in its mind'
        action={
          <Button
            size='sm'
            disabled={busy !== null || subject === null || !attribute}
            disabledReason={
              busy ??
              (subject === null
                ? 'Choose whom it concerns.'
                : attribute
                  ? undefined
                  : 'Choose what it believes about them.')
            }
            onClick={() => subject !== null && set.mutate(subject)}
          >
            <Plus />
            Believe it
          </Button>
        }
      >
        <NodePicker
          label='About'
          types={BEINGS}
          value={subject}
          onChange={setSubject}
          blocked={busy}
        />
        <MindPicker
          label='What'
          value={attribute}
          table={table(view.belief_attributes)}
          blocked={busy}
          onPick={setAttribute}
        />
        <MindPicker
          label='Learned by'
          value={source}
          table={table(view.belief_sources)}
          blocked={busy}
          onPick={setSource}
        />
        <div className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor={`belief-value-${view.node_id}`}>
            Believed value
          </Label>
          <Input
            id={`belief-value-${view.node_id}`}
            type='number'
            value={value}
            disabled={busy !== null}
            onChange={(event) => setValue(Number(event.target.value) || 0)}
          />
        </div>
      </AddBar>
    </MindCard>
  )
}

export function IntrigueSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const query = useIntrigue(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section
        id='section-intrigue'
        title='Secrets and schemes'
        icon={INTRIGUE_ICON}
      >
        <EmptyState
          icon={INTRIGUE_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view) return null
  const ctx: Ctx = { view, blocked: reason(), hold }
  const open = view.schemes.filter((scheme) => OPEN_PHASES.has(scheme.phase))
  return (
    <Section
      id='section-intrigue'
      title='Secrets and schemes'
      description='The secrets it keeps and knows, the hooks and favours that bind it to others, any false name it lives under, the schemes it plots or suffers, its true name and what it believes of the world.'
      icon={INTRIGUE_ICON}
    >
      <div className='@container/mind flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-2 gap-3 @lg/mind:grid-cols-3 @4xl/mind:grid-cols-6'>
          <KpiTile
            label='Secrets kept'
            value={view.secrets.length}
            icon={SECRET_ICON}
            tone='warning'
          />
          <KpiTile
            label='Secrets known'
            value={view.known_secrets.length}
            icon={WITNESS_ICON}
            tone='info'
          />
          <KpiTile
            label='Hooks held'
            value={
              view.hooks_held.filter((hook) => hook.used_epoch === null).length
            }
            icon={HOOK_ICON}
            tone='danger'
          />
          <KpiTile
            label='Favours due'
            value={
              view.favours_due.filter((favour) => favour.called_epoch === null)
                .length
            }
            icon={FAVOUR_ICON}
            tone='gold'
          />
          <KpiTile
            label='Open schemes'
            value={open.length}
            icon={SCHEME_ICON}
            tone='verdigris'
          />
          <KpiTile
            label='Beliefs'
            value={view.beliefs.length}
            icon={BELIEF_ICON}
            tone='muted'
          />
        </div>
        <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
          <SecretsCard ctx={ctx} />
          <HooksCard ctx={ctx} />
          <FavoursCard ctx={ctx} />
          <IdentityCard ctx={ctx} />
          <SchemesCard ctx={ctx} />
          <TrueNameCard ctx={ctx} />
          <BeliefsCard ctx={ctx} />
        </div>
        <ControlPanel
          title='Hold what you set'
          note='Weights, strengths, masks, schemes, names and beliefs you set are held against the world while the switch is on. Every change goes into the ledger and can be undone.'
          hold={hold}
          onHold={setHold}
        >
          {null}
        </ControlPanel>
      </div>
    </Section>
  )
}
