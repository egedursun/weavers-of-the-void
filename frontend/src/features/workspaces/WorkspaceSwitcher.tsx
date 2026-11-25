import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Check, ChevronsUpDown, Plus } from 'lucide-react'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Muted, Text } from '@/components/typography'
import { CreateWorkspaceDialog } from './CreateWorkspaceDialog'
import { WorkspaceCrest } from './WorkspaceCrest'
import { TEAM_PART_LOOK, type TeamPart } from './teamParts'
import { type Workspace } from './types'
import { useActiveWorkspace, useSwitchWorkspace } from './useActiveWorkspace'
import { WORKSPACE_KIND_LOOK, WORKSPACE_ROLE_LOOK } from './workspaceLook'

const TEAM_MENU: readonly TeamPart[] = ['members', 'universes', 'general']

function WorkspaceLine({ workspace }: { workspace: Workspace }) {
  const kind = WORKSPACE_KIND_LOOK[workspace.kind]
  return (
    <span className='flex min-w-0 flex-1 flex-col'>
      <Text as='span' truncate>
        {workspace.name}
      </Text>
      <Muted as='span' variant='caption' truncate>
        {`${kind.label} · ${WORKSPACE_ROLE_LOOK[workspace.role].label} · ${plural(workspace.universe_count, 'universe')}`}
      </Muted>
    </span>
  )
}

export function WorkspaceSwitcher({ compact = false }: { compact?: boolean }) {
  const { workspaces, list, active } = useActiveWorkspace()
  const switchTo = useSwitchWorkspace()
  const navigate = useNavigate()
  const [creating, setCreating] = useState(false)
  const name = active?.name ?? 'Workspace'
  const personal = list.filter((workspace) => workspace.kind === 'personal')
  const teams = list.filter((workspace) => workspace.kind === 'team')
  const groups: [string, Workspace[]][] = [
    ['Your own', personal],
    ['Teams', teams],
  ]
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type='button'
            variant='outline'
            size='sm'
            aria-label={`${name}: switch workspace`}
            disabled={workspaces.isPending}
            disabledReason='Reading your workspaces.'
            className={cn('max-w-80', compact && 'max-w-32')}
          >
            <WorkspaceCrest name={name} size='xs' />
            <span className={cn('min-w-0 truncate', compact && 'sr-only')}>
              {name}
            </span>
            <ChevronsUpDown />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align='end' className='w-80'>
          {active && (
            <>
              <DropdownMenuLabel className='flex min-w-0 items-center gap-2'>
                <WorkspaceCrest name={active.name} size='sm' />
                <WorkspaceLine workspace={active} />
                <Badge variant='outline' size='sm'>
                  {WORKSPACE_KIND_LOOK[active.kind].label}
                </Badge>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
            </>
          )}
          {groups.map(([title, items]) => (
            <DropdownMenuGroup key={title}>
              <DropdownMenuLabel>
                <Muted as='span' variant='caption'>
                  {items.length === 0 ? `${title}: none yet` : title}
                </Muted>
              </DropdownMenuLabel>
              {items.map((workspace) => (
                <DropdownMenuItem
                  key={workspace.id}
                  onSelect={() => {
                    if (workspace.id !== active?.id) switchTo(workspace)
                  }}
                  className='flex min-w-0 items-center gap-2'
                >
                  <WorkspaceCrest name={workspace.name} size='xs' />
                  <WorkspaceLine workspace={workspace} />
                  {workspace.id === active?.id && (
                    <Check
                      aria-hidden='true'
                      className='size-icon-sm shrink-0 text-primary'
                    />
                  )}
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => setCreating(true)}>
            <Plus />
            Found a team workspace
          </DropdownMenuItem>
          {TEAM_MENU.map((part) => {
            const look = TEAM_PART_LOOK[part]
            const Icon = look.icon
            return (
              <DropdownMenuItem
                key={part}
                disabled={active === null}
                onSelect={() =>
                  void navigate({ to: '/workspace', search: { part } })
                }
              >
                <Icon />
                {look.menu}
              </DropdownMenuItem>
            )
          })}
        </DropdownMenuContent>
      </DropdownMenu>
      <CreateWorkspaceDialog
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={(workspace) => {
          setCreating(false)
          switchTo(workspace)
        }}
      />
    </>
  )
}
