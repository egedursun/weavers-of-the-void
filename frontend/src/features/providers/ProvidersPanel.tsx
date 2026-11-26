import { useMemo, useState } from 'react'
import {
  CircleAlert,
  CloudCog,
  Plug,
  Route,
  ShieldCheck,
  TriangleAlert,
  UserRound,
  Users,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  IntroNote,
  LoadingBlock,
  Medallion,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { AddConnectionDialog } from './AddConnectionDialog'
import { ConnectionActs, type PendingAct } from './ConnectionActs'
import { type ConnectionAct, ConnectionCard } from './ConnectionCard'
import { LoginDialog } from './LoginDialog'
import { RoleChain } from './RoleChain'
import { useProviders } from './api'
import { FAMILIES, FAMILY_LOOK } from './providerLook'
import {
  type ProviderConnection,
  type ProviderKindView,
  type ProviderScope,
  type ProvidersView,
} from './types'

const VIEWER_REASON = 'Only administrators of the workspace change its models.'

function ScopeHeader({
  scope,
  view,
}: {
  scope: ProviderScope
  view: ProvidersView
}) {
  const icon = scope === 'server' ? CloudCog : view.personal ? UserRound : Users
  const title =
    scope === 'server'
      ? 'The server default'
      : view.personal
        ? 'Your personal workspace'
        : 'This team workspace'
  const lead =
    scope === 'server'
      ? 'Every workspace on this server uses these for a role it has not set itself. Only API keys and local servers belong here, so no one shares a personal subscription.'
      : view.personal
        ? 'Only you work here, so a subscription of your own may be logged in. A role you leave empty uses the server default.'
        : 'Everyone in this workspace shares these. Subscriptions are personal and stay out; a role you leave empty uses the server default.'
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-3 rounded-md p-3 sealed-well'>
      <Medallion
        icon={icon}
        tone={scope === 'server' ? 'info' : 'gold'}
        size='sm'
      />
      <div className='flex min-w-0 flex-1 basis-60 flex-col gap-0.5'>
        <Text as='span' weight='medium'>
          {title}
        </Text>
        <Muted as='span' variant='caption'>
          {lead}
        </Muted>
      </div>
      <Badge variant={view.gateway_ready ? 'success' : 'warning'} size='sm'>
        {view.gateway_ready ? <ShieldCheck /> : <TriangleAlert />}
        {view.gateway_ready
          ? 'The gateway for API keys is ready'
          : 'No gateway: API keys wait until AERONA_GATEWAY_URL is set'}
      </Badge>
    </div>
  )
}

const CONNECTIONS_SHOWN = 8

function FamilyConnections({
  label,
  empty,
  listed,
  kinds,
  scope,
  editable,
  readOnlyReason,
  onAct,
}: {
  label: string
  empty: string
  listed: ProviderConnection[]
  kinds: Map<string, ProviderKindView>
  scope: ProviderScope
  editable: boolean
  readOnlyReason: string
  onAct: (act: ConnectionAct, connection: ProviderConnection) => void
}) {
  const page = useShowMore(listed, CONNECTIONS_SHOWN)
  if (page.total === 0)
    return (
      <Muted variant='caption' className='rounded-md p-3 sealed-well'>
        {empty}
      </Muted>
    )
  return (
    <>
      <ul
        aria-label={`Connected ${label.toLowerCase()}`}
        className='flex min-w-0 flex-col gap-2'
      >
        {page.visible.map((connection) => {
          const kind = kinds.get(connection.kind)
          if (!kind) return null
          return (
            <ConnectionCard
              key={connection.id}
              connection={connection}
              kind={kind}
              editable={editable}
              readOnlyReason={readOnlyReason}
              canLogIn={scope !== 'server'}
              onAct={(act) => onAct(act, connection)}
            />
          )
        })}
      </ul>
      <ShowMore state={page} noun={['connection', 'connections']} />
    </>
  )
}

function Connections({
  scope,
  view,
  kinds,
  readOnlyReason,
  onAct,
  onAdd,
}: {
  scope: ProviderScope
  view: ProvidersView
  kinds: Map<string, ProviderKindView>
  readOnlyReason: string
  onAct: (act: ConnectionAct, connection: ProviderConnection) => void
  onAdd: () => void
}) {
  return (
    <Section
      title='Connections'
      description='What this scope may think and draw with. A connection serves only the roles it is put in below.'
      icon={Plug}
      surface='card'
      level={3}
      actions={
        <Button
          type='button'
          disabled={!view.editable}
          disabledReason={readOnlyReason}
          onClick={onAdd}
        >
          <Plug />
          Connect a provider
        </Button>
      }
    >
      <div className='flex min-w-0 flex-col gap-4'>
        {FAMILIES.map((family) => {
          const look = FAMILY_LOOK[family]
          const listed = view.connections.filter(
            (item) => kinds.get(item.kind)?.family === family
          )
          const refusal =
            view.kinds.find(
              (kind) => kind.family === family && kind.refusal !== null
            )?.refusal ?? null
          return (
            <section
              key={family}
              aria-label={look.label}
              className='flex min-w-0 flex-col gap-2'
            >
              <span className='flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5'>
                <look.icon
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-muted-foreground'
                />
                <Label>{look.label}</Label>
                <Muted as='span' variant='caption'>
                  {refusal ?? look.lead}
                </Muted>
              </span>
              {(refusal === null || listed.length > 0) && (
                <FamilyConnections
                  label={look.label}
                  empty={look.empty}
                  listed={listed}
                  kinds={kinds}
                  scope={scope}
                  editable={view.editable}
                  readOnlyReason={readOnlyReason}
                  onAct={onAct}
                />
              )}
            </section>
          )
        })}
      </div>
    </Section>
  )
}

export function ProvidersPanel({ scope }: { scope: ProviderScope }) {
  const providers = useProviders(scope)
  const [adding, setAdding] = useState(false)
  const [pending, setPending] = useState<PendingAct | null>(null)
  const [loggingIn, setLoggingIn] = useState<ProviderConnection | null>(null)
  const view = providers.data
  const kinds = useMemo(
    () => new Map((view?.kinds ?? []).map((kind) => [kind.kind, kind])),
    [view?.kinds]
  )
  if (providers.isPending) return <LoadingBlock label='Reading the providers' />
  if (providers.isError || !view)
    return (
      <EmptyState
        size='compact'
        icon={CircleAlert}
        title='The providers could not be read'
        description={providers.error?.message ?? 'Try again in a moment.'}
        action={
          <Button
            type='button'
            variant='outline'
            onClick={() => void providers.refetch()}
          >
            Try again
          </Button>
        }
      />
    )
  const readOnlyReason =
    scope === 'server'
      ? 'Only server owners and administrators change the server default.'
      : VIEWER_REASON
  const act = (next: ConnectionAct, connection: ProviderConnection) => {
    if (next === 'login') setLoggingIn(connection)
    else setPending({ act: next, connection })
  }
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <ScopeHeader scope={scope} view={view} />
      {!view.editable && <IntroNote>{readOnlyReason}</IntroNote>}
      <Connections
        scope={scope}
        view={view}
        kinds={kinds}
        readOnlyReason={readOnlyReason}
        onAct={act}
        onAdd={() => setAdding(true)}
      />
      <Section
        title='Models for each role'
        description='Each role tries its models in order; when one cannot answer, the next one serves.'
        icon={Route}
        surface='card'
        level={3}
      >
        <div className='flex min-w-0 flex-col gap-3'>
          {view.roles.map((role) => (
            <RoleChain
              key={`${role.role}:${role.entries.map((entry) => `${entry.id}.${entry.connection_id}.${entry.model}`).join(',')}`}
              scope={scope}
              role={role}
              connections={view.connections}
              kinds={kinds}
              editable={view.editable}
              readOnlyReason={readOnlyReason}
            />
          ))}
        </div>
      </Section>
      <AddConnectionDialog
        scope={scope}
        kinds={view.kinds}
        open={adding}
        onClose={() => setAdding(false)}
        onAdded={(connection, kind) => {
          if (kind.family === 'subscription') setLoggingIn(connection)
        }}
      />
      <ConnectionActs
        scope={scope}
        pending={pending}
        onDone={() => setPending(null)}
      />
      {scope !== 'server' && loggingIn && (
        <LoginDialog
          workspaceId={scope.workspaceId}
          connection={loggingIn}
          terms={kinds.get(loggingIn.kind)?.terms ?? null}
          open
          onClose={() => setLoggingIn(null)}
        />
      )}
    </div>
  )
}
