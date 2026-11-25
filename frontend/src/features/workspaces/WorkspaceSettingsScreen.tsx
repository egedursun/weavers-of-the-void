import { useState } from 'react'
import { CircleAlert, LibraryBig, Settings2, UsersRound } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, IntroNote, LoadingBlock } from '@/components/domain'
import { GeneralPanel } from './GeneralPanel'
import { MembersPanel } from './MembersPanel'
import { SettingsPage } from './SettingsPage'
import { UniverseAccessPanel } from './UniverseAccessPanel'
import { WorkspaceCrest } from './WorkspaceCrest'
import { useMembers } from './api'
import { useActiveWorkspace } from './useActiveWorkspace'
import { WORKSPACE_KIND_LOOK, WORKSPACE_ROLE_LOOK } from './workspaceLook'

type Part = 'general' | 'members' | 'universes'

const PARTS: readonly Part[] = ['general', 'members', 'universes']

export function WorkspaceSettingsScreen() {
  const { workspaces, active } = useActiveWorkspace()
  const members = useMembers(active?.id ?? null)
  const [part, setPart] = useState<Part>('general')
  if (workspaces.isPending)
    return (
      <SettingsPage
        title='Workspace settings'
        lead='Reading your workspaces.'
        crest={null}
      >
        <LoadingBlock label='Reading your workspaces' />
      </SettingsPage>
    )
  if (workspaces.isError || active === null)
    return (
      <SettingsPage
        title='Workspace settings'
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
          ? 'Who works here, in which role, and the rare exceptions for one universe.'
          : 'Who works here and in which role. Only administrators change it.'
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
          setPart(PARTS.find((item) => item === value) ?? 'general')
        }
      >
        <TabsList aria-label='Parts of the workspace settings'>
          <TabsTrigger value='general'>
            <Settings2 />
            General
          </TabsTrigger>
          <TabsTrigger value='members'>
            <UsersRound />
            Members
          </TabsTrigger>
          <TabsTrigger value='universes'>
            <LibraryBig />
            Universes
          </TabsTrigger>
        </TabsList>
        <TabsContent value='general'>
          <GeneralPanel
            key={active.id}
            workspace={active}
            lastAdmin={lastAdmin}
          />
        </TabsContent>
        <TabsContent value='members'>
          <MembersPanel key={active.id} workspace={active} />
        </TabsContent>
        <TabsContent value='universes'>
          <UniverseAccessPanel key={active.id} workspace={active} />
        </TabsContent>
      </Tabs>
    </SettingsPage>
  )
}
