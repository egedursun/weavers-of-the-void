import { useNavigate, useSearch } from '@tanstack/react-router'
import { CircleAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, IntroNote, LoadingBlock } from '@/components/domain'
import { ServerAccountsPanel } from '@/features/accounts/ServerAccountsPanel'
import { managesAccounts } from '@/features/accounts/accountLook'
import { useSignedInAccount } from '@/features/accounts/api'
import { ModelsSettings } from '@/features/providers/ModelsSettings'
import { GeneralPanel } from './GeneralPanel'
import { MembersPanel } from './MembersPanel'
import { SettingsPage } from './SettingsPage'
import { UniverseAccessPanel } from './UniverseAccessPanel'
import { WorkspaceCrest } from './WorkspaceCrest'
import { useMembers } from './api'
import { TEAM_PARTS, TEAM_PART_LOOK, type TeamPart } from './teamParts'
import { useActiveWorkspace } from './useActiveWorkspace'
import { WORKSPACE_KIND_LOOK, WORKSPACE_ROLE_LOOK } from './workspaceLook'

export function WorkspaceSettingsScreen() {
  const { workspaces, active } = useActiveWorkspace()
  const members = useMembers(active?.id ?? null)
  const search = useSearch({ from: '/workspace' })
  const navigate = useNavigate({ from: '/workspace' })
  const me = useSignedInAccount()
  const parts = TEAM_PARTS.filter(
    (item) =>
      item !== 'accounts' || (me !== null && managesAccounts(me.server_role))
  )
  const part: TeamPart = parts.find((item) => item === search.part) ?? 'members'
  const choose = (next: TeamPart, add = false) =>
    void navigate({
      search: { part: next, ...(add ? { add: true } : {}) },
      replace: true,
    })
  if (workspaces.isPending)
    return (
      <SettingsPage
        title='Team and workspace'
        lead='Reading your workspaces.'
        crest={null}
      >
        <LoadingBlock label='Reading your workspaces' />
      </SettingsPage>
    )
  if (workspaces.isError || active === null)
    return (
      <SettingsPage
        title='Team and workspace'
        lead='Your workspaces could not be read.'
        crest={null}
      >
        <EmptyState
          icon={CircleAlert}
          title='No workspace to show'
          description={
            workspaces.isError
              ? workspaces.error.message
              : 'You belong to no workspace yet.'
          }
          action={
            <Button
              type='button'
              variant='outline'
              onClick={() => void workspaces.refetch()}
            >
              Try again
            </Button>
          }
        />
      </SettingsPage>
    )
  const kind = WORKSPACE_KIND_LOOK[active.kind]
  const role = WORKSPACE_ROLE_LOOK[active.role]
  const RoleIcon = role.icon
  const KindIcon = kind.icon
  const admins = (members.data ?? []).filter(
    (member) => member.role === 'admin'
  ).length
  const lastAdmin = active.role === 'admin' && admins <= 1
  return (
    <SettingsPage
      title={active.name}
      lead={
        active.role === 'admin'
          ? 'Everyone who works in this workspace, their roles, who reaches each universe, the models it thinks with, and the workspace itself.'
          : 'Who works in this workspace and in which role. Only its administrators change it.'
      }
      crest={
        <div className='flex min-w-0 flex-col items-center gap-2'>
          <WorkspaceCrest name={active.name} size='md' />
          <span className='flex flex-wrap justify-center gap-1.5'>
            <Badge variant='outline' size='sm'>
              <KindIcon />
              {kind.label}
            </Badge>
            <Badge variant='secondary' size='sm'>
              <RoleIcon />
              {`You are ${role.label}`}
            </Badge>
          </span>
        </div>
      }
    >
      {active.role !== 'admin' && (
        <IntroNote>
          You see this workspace as {role.label}. Its administrators manage
          members and access; everything here is shown so you know who works
          beside you.
        </IntroNote>
      )}
      <Tabs
        value={part}
        onValueChange={(value) =>
          choose(parts.find((item) => item === value) ?? 'members')
        }
      >
        <TabsList aria-label='Parts of the team and workspace'>
          {parts.map((item) => {
            const look = TEAM_PART_LOOK[item]
            const Icon = look.icon
            return (
              <TabsTrigger key={item} value={item}>
                <Icon />
                {look.label}
              </TabsTrigger>
            )
          })}
        </TabsList>
        <TabsContent value='members'>
          <MembersPanel
            key={active.id}
            workspace={active}
            adding={search.add === true}
            onAdding={(open) => choose('members', open)}
          />
        </TabsContent>
        <TabsContent value='universes'>
          <UniverseAccessPanel key={active.id} workspace={active} />
        </TabsContent>
        <TabsContent value='providers'>
          <ModelsSettings
            workspaceId={active.id}
            showServer={me !== null && managesAccounts(me.server_role)}
          />
        </TabsContent>
        <TabsContent value='general'>
          <GeneralPanel
            key={active.id}
            workspace={active}
            lastAdmin={lastAdmin}
          />
        </TabsContent>
        {parts.includes('accounts') && (
          <TabsContent value='accounts'>
            <ServerAccountsPanel />
          </TabsContent>
        )}
      </Tabs>
    </SettingsPage>
  )
}
