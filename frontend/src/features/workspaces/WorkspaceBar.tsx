import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { UserPlus, UsersRound } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CreateWorkspaceDialog } from './CreateWorkspaceDialog'
import { WorkspaceSwitcher } from './WorkspaceSwitcher'
import { useActiveWorkspace, useSwitchWorkspace } from './useActiveWorkspace'

export function MembersButton({ compact = false }: { compact?: boolean }) {
  const { workspaces, active } = useActiveWorkspace()
  const navigate = useNavigate()
  const switchTo = useSwitchWorkspace()
  const [founding, setFounding] = useState(false)
  const personal = active?.kind === 'personal'
  const label = personal ? 'Work with others' : 'Members'
  const Icon = personal ? UserPlus : UsersRound
  return (
    <>
      <Button
        type='button'
        variant='outline'
        size='sm'
        aria-label={
          personal
            ? 'Work with others: found a team workspace'
            : `Members of ${active?.name ?? 'this workspace'}`
        }
        disabled={workspaces.isPending || active === null}
        disabledReason='Reading your workspaces.'
        onClick={() =>
          personal
            ? setFounding(true)
            : void navigate({ to: '/workspace', search: { part: 'members' } })
        }
      >
        <Icon />
        <span className={cn(compact && 'sr-only')}>{label}</span>
        {!personal && active && (
          <Badge variant='secondary' size='sm'>
            {active.member_count}
          </Badge>
        )}
      </Button>
      <CreateWorkspaceDialog
        open={founding}
        onClose={() => setFounding(false)}
        onCreated={(created) => {
          setFounding(false)
          switchTo(created, { part: 'members', add: true })
        }}
      />
    </>
  )
}

export function WorkspaceBar({ compact = false }: { compact?: boolean }) {
  return (
    <span className='flex min-w-0 flex-wrap items-center gap-2'>
      <WorkspaceSwitcher compact={compact} />
      <MembersButton compact={compact} />
    </span>
  )
}
