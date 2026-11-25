import { useState } from 'react'
import {
  BookLock,
  CircleAlert,
  LibraryBig,
  RotateCcw,
  ShieldCheck,
  Undo2,
  UsersRound,
} from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  LoadingBlock,
  Medallion,
  PanelGrid,
  Paged,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { AccountAvatar } from '@/features/accounts/AccountAvatar'
import { useSignedInAccount } from '@/features/accounts/api'
import { UniverseCrest } from '@/features/universes/UniverseCrest'
import { useShelf } from '@/features/universes/api'
import {
  useResetPermissions,
  useSetCanonApproval,
  useSetOverride,
  useSetPermission,
  useUniverseAccess,
} from './api'
import {
  type AccessPerson,
  type PermissionRow,
  type TunedRole,
  type UniverseAccess,
  type UniverseRole,
  type Workspace,
} from './types'
import {
  OVERRIDE_ROLES,
  PERMISSION_ICON,
  UNIVERSE_ROLE_LOOK,
  WORKSPACE_ROLE_LOOK,
} from './workspaceLook'

const PEOPLE_SHOWN = 10
const WORKSPACE_ROLE = 'workspace'
const TUNED: readonly TunedRole[] = ['editor', 'viewer']
const ADMIN_ONLY = 'Only administrators of this universe change its access.'

function PersonRow({
  person,
  universeId,
  workspaceId,
  manage,
}: {
  person: AccessPerson
  universeId: string
  workspaceId: number
  manage: boolean
}) {
  const set = useSetOverride()
  const { account } = person
  const effective = UNIVERSE_ROLE_LOOK[person.role]
  const EffectiveIcon = effective.icon
  const reason = !manage
    ? ADMIN_ONLY
    : set.isPending
      ? 'The role is being changed.'
      : null
  const choose = (role: UniverseRole | null) =>
    set.mutate(
      { id: workspaceId, universeId, accountId: account.id, role },
      {
        onSuccess: () =>
          toast.success(
            role === null
              ? `${account.display_name} is back to the workspace role`
              : `${account.display_name} is ${UNIVERSE_ROLE_LOOK[role].label} here`
          ),
        onError: (error) => toast.error(error.message),
      }
    )
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-3 rounded-md surface-sheen px-3 py-2'>
      <AccountAvatar
        name={account.display_name}
        tone={account.avatar_tone}
        size='sm'
        dimmed={account.status !== 'active'}
      />
      <span className='flex min-w-0 flex-1 basis-40 flex-col'>
        <Text as='span' weight='semibold' truncate>
          {account.display_name}
        </Text>
        <Muted as='span' variant='caption' truncate>
          {`${WORKSPACE_ROLE_LOOK[person.workspace_role].label} of the workspace`}
        </Muted>
      </span>
      <span className='flex min-w-0 flex-wrap items-center gap-2'>
        <Badge
          variant={person.role === 'none' ? 'destructive' : 'outline'}
          size='sm'
        >
          <EffectiveIcon />
          {effective.label}
        </Badge>
        {person.overridden && (
          <Badge variant='warning' size='sm'>
            Exception
          </Badge>
        )}
        <Select
          act={set}
          value={person.overridden ? person.role : WORKSPACE_ROLE}
          disabled={reason !== null}
          onValueChange={(value) => {
            if (value === WORKSPACE_ROLE) return choose(null)
            const role = OVERRIDE_ROLES.find((item) => item === value)
            if (role) choose(role)
          }}
        >
          <SelectTrigger
            size='sm'
            className='w-52'
            aria-label={`Role of ${account.display_name} in this universe`}
            title={reason ?? undefined}
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={WORKSPACE_ROLE}>
              {`Workspace role (${WORKSPACE_ROLE_LOOK[person.workspace_role].label})`}
            </SelectItem>
            {OVERRIDE_ROLES.map((role) => {
              const Icon = UNIVERSE_ROLE_LOOK[role].icon
              return (
                <SelectItem key={role} value={role}>
                  <Icon aria-hidden='true' />
                  {UNIVERSE_ROLE_LOOK[role].label}
                </SelectItem>
              )
            })}
          </SelectContent>
        </Select>
        <Button
          act={set}
          type='button'
          size='sm'
          variant='ghost'
          disabled={!person.overridden || reason !== null}
          disabledReason={
            person.overridden
              ? (reason ?? '')
              : 'They already have their workspace role here.'
          }
          onClick={() => choose(null)}
        >
          <Undo2 />
          Back to the workspace role
        </Button>
      </span>
    </li>
  )
}

const ROLE_FIELDS: Record<
  TunedRole,
  {
    allowed: (row: PermissionRow) => boolean
    standard: (row: PermissionRow) => boolean
  }
> = {
  editor: {
    allowed: (row) => row.editor,
    standard: (row) => row.editor_default,
  },
  viewer: {
    allowed: (row) => row.viewer,
    standard: (row) => row.viewer_default,
  },
}

function PermissionTable({
  access,
  manage,
}: {
  access: UniverseAccess
  manage: boolean
}) {
  const set = useSetPermission()
  const reset = useResetPermissions()
  const target = { id: access.workspace_id, universeId: access.universe_id }
  const changed = access.permissions.flatMap((row) =>
    TUNED.filter(
      (role) =>
        ROLE_FIELDS[role].allowed(row) !== ROLE_FIELDS[role].standard(row)
    )
  ).length
  const reason = !manage
    ? ADMIN_ONLY
    : set.isPending || reset.isPending
      ? 'A permission is being saved.'
      : null
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Muted variant='caption'>
          {changed === 0
            ? 'Every permission is at its default. Most teams never change these.'
            : `${changed === 1 ? 'One switch differs' : `${changed} switches differ`} from the defaults.`}
        </Muted>
        <Button
          act={reset}
          type='button'
          size='sm'
          variant='outline'
          disabled={changed === 0 || reason !== null}
          disabledReason={
            changed === 0 ? 'Everything is at its default.' : (reason ?? '')
          }
          onClick={() =>
            reset.mutate(target, {
              onSuccess: () =>
                toast.success('Every permission is back to its default'),
              onError: (error) => toast.error(error.message),
            })
          }
        >
          <RotateCcw />
          Back to defaults
        </Button>
      </div>
      <ul
        aria-label='Permissions of each role'
        className='flex min-w-0 flex-col gap-1.5'
      >
        <Paged
          items={access.permissions}
          initial={access.permissions.length}
          as='li'
        >
          {(row) => (
            <li
              key={row.permission}
              className='flex min-w-0 flex-wrap items-center gap-3 rounded-md surface-sheen px-3 py-2'
            >
              <Medallion
                icon={PERMISSION_ICON[row.permission]}
                tone='gold'
                size='sm'
              />
              <span className='flex min-w-0 flex-1 basis-56 flex-col'>
                <Text as='span' weight='semibold'>
                  {row.label}
                </Text>
                <Muted as='span' variant='caption'>
                  {row.meaning}
                </Muted>
              </span>
              <span className='flex min-w-0 flex-wrap items-center gap-4'>
                {TUNED.map((role) => {
                  const allowed = ROLE_FIELDS[role].allowed(row)
                  const standard = ROLE_FIELDS[role].standard(row)
                  const fixed = row.permission === 'view'
                  return (
                    <label
                      key={role}
                      className='flex min-w-0 items-center gap-2'
                      title={
                        fixed
                          ? 'Everyone with access reads the universe.'
                          : (reason ??
                            `Default: ${standard ? 'allowed' : 'not allowed'}`)
                      }
                    >
                      <Switch
                        act={set}
                        checked={allowed}
                        disabled={fixed || reason !== null}
                        aria-label={`${UNIVERSE_ROLE_LOOK[role].label}s: ${row.label}`}
                        onCheckedChange={(next) =>
                          set.mutate(
                            {
                              ...target,
                              changes: { [role]: { [row.permission]: next } },
                            },
                            { onError: (error) => toast.error(error.message) }
                          )
                        }
                      />
                      <Text as='span' variant='caption' weight='medium'>
                        {UNIVERSE_ROLE_LOOK[role].label}
                      </Text>
                      {allowed !== standard && (
                        <Badge variant='warning' size='sm'>
                          Changed
                        </Badge>
                      )}
                    </label>
                  )
                })}
              </span>
            </li>
          )}
        </Paged>
      </ul>
    </div>
  )
}

function CanonApproval({
  access,
  manage,
}: {
  access: UniverseAccess
  manage: boolean
}) {
  const set = useSetCanonApproval()
  const reason = !manage
    ? ADMIN_ONLY
    : set.isPending
      ? 'The setting is being saved.'
      : null
  return (
    <label
      className={cn(
        'flex min-w-0 items-center gap-3 rounded-md surface-sheen px-3 py-3',
        access.canon_approval && 'border-primary'
      )}
      title={reason ?? undefined}
    >
      <Medallion
        icon={BookLock}
        tone={access.canon_approval ? 'gold' : 'muted'}
        size='sm'
      />
      <span className='flex min-w-0 flex-1 flex-col'>
        <Text as='span' weight='semibold'>
          {access.canon_approval
            ? 'Canon approval is on'
            : 'Canon approval is off'}
        </Text>
        <Muted as='span' variant='caption'>
          When on, an Editor's act that touches locked canon waits as a proposal
          until an administrator approves it. Administrators' own acts never
          wait.
        </Muted>
      </span>
      <Switch
        act={set}
        checked={access.canon_approval}
        disabled={reason !== null}
        aria-label='Canon approval'
        onCheckedChange={(enabled) =>
          set.mutate(
            {
              id: access.workspace_id,
              universeId: access.universe_id,
              on: enabled,
            },
            {
              onSuccess: () =>
                toast.success(
                  enabled
                    ? 'Editors now propose changes to locked canon'
                    : 'Editors change locked canon directly again'
                ),
              onError: (error) => toast.error(error.message),
            }
          )
        }
      />
    </label>
  )
}

export function AccessOf({
  workspace,
  universeId,
}: {
  workspace: Workspace
  universeId: string
}) {
  const access = useUniverseAccess({ id: workspace.id, universeId })
  const me = useSignedInAccount()
  const page = useShowMore(access.data?.people ?? [], PEOPLE_SHOWN)
  if (access.isPending) return <LoadingBlock label='Reading who reaches it' />
  if (access.isError)
    return (
      <EmptyState
        size='compact'
        icon={CircleAlert}
        title='The access could not be read'
        description={access.error.message}
        action={
          <Button
            type='button'
            variant='outline'
            onClick={() => void access.refetch()}
          >
            Try again
          </Button>
        }
      />
    )
  const data = access.data
  const mine = data.people.find((person) => person.account.id === me?.id)
  const manage = workspace.role === 'admin' || mine?.role === 'admin'
  return (
    <PanelGrid>
      <Section
        title={`Who reaches ${data.universe_name}`}
        icon={UsersRound}
        surface='card'
        level={3}
      >
        {page.total === 0 ? (
          <EmptyState
            size='compact'
            icon={UsersRound}
            title='Nobody else yet'
            description='Members of the workspace reach every universe with their workspace role.'
          />
        ) : (
          <>
            <ul
              aria-label='People with access'
              className='flex min-w-0 flex-col gap-2'
            >
              {page.visible.map((person) => (
                <PersonRow
                  key={person.account.id}
                  person={person}
                  universeId={data.universe_id}
                  workspaceId={data.workspace_id}
                  manage={manage}
                />
              ))}
            </ul>
            <ShowMore state={page} noun={['person', 'people']} />
          </>
        )}
      </Section>
      <Section
        title='What each role may do'
        icon={ShieldCheck}
        surface='card'
        level={3}
      >
        <CanonApproval access={data} manage={manage} />
        <PermissionTable access={data} manage={manage} />
      </Section>
    </PanelGrid>
  )
}

export function UniverseAccessPanel({ workspace }: { workspace: Workspace }) {
  const shelf = useShelf()
  const universes = shelf.data?.items ?? []
  const [chosen, setChosen] = useState<string | null>(null)
  const current =
    universes.find((item) => item.id === chosen) ?? universes[0] ?? null
  if (shelf.isPending) return <LoadingBlock label='Reading the shelves' />
  if (shelf.isError)
    return (
      <EmptyState
        size='compact'
        icon={CircleAlert}
        title='The shelves could not be read'
        description={shelf.error.message}
        action={
          <Button
            type='button'
            variant='outline'
            onClick={() => void shelf.refetch()}
          >
            Try again
          </Button>
        }
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div className='flex min-w-0 flex-wrap items-center gap-3 rounded-md surface-well p-3'>
        {current && <UniverseCrest name={current.name} size='sm' />}
        <span className='flex min-w-0 flex-1 basis-48 flex-col'>
          <Text as='span' weight='semibold'>
            Access to one universe
          </Text>
          <Muted as='span' variant='caption'>
            Members reach every universe with their workspace role. Set an
            exception here only when one universe needs it.
          </Muted>
        </span>
        <Select
          value={current?.id ?? ''}
          disabled={universes.length === 0}
          onValueChange={setChosen}
        >
          <SelectTrigger
            className='w-64'
            aria-label='Universe'
            title={
              universes.length === 0
                ? 'No universe stands in this workspace yet.'
                : undefined
            }
          >
            <SelectValue placeholder='No universe yet' />
          </SelectTrigger>
          <SelectContent>
            {universes.map((universe) => (
              <SelectItem key={universe.id} value={universe.id}>
                {universe.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {current === null ? (
        <EmptyState
          size='compact'
          icon={LibraryBig}
          title='No universe in this workspace yet'
          description='Create or import one in the library; it appears here with everyone who reaches it.'
        />
      ) : (
        <AccessOf
          key={current.id}
          workspace={workspace}
          universeId={current.id}
        />
      )}
    </div>
  )
}
