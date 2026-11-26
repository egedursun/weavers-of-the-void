import { useState } from 'react'
import { CloudCog, UserRound } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ProvidersPanel } from './ProvidersPanel'

type ModelsScope = 'workspace' | 'server'

export function ModelsSettings({
  workspaceId,
  showServer,
}: {
  workspaceId: number
  showServer: boolean
}) {
  const [shown, setShown] = useState<ModelsScope>('workspace')
  if (!showServer)
    return <ProvidersPanel key={workspaceId} scope={{ workspaceId }} />
  return (
    <Tabs
      value={shown}
      onValueChange={(value) =>
        setShown(value === 'server' ? 'server' : 'workspace')
      }
      className='flex min-w-0 flex-col gap-4'
    >
      <TabsList size='sm' aria-label='Whose models to set'>
        <TabsTrigger value='workspace'>
          <UserRound />
          This workspace
        </TabsTrigger>
        <TabsTrigger value='server'>
          <CloudCog />
          Server default
        </TabsTrigger>
      </TabsList>
      <TabsContent value='workspace'>
        <ProvidersPanel key={workspaceId} scope={{ workspaceId }} />
      </TabsContent>
      <TabsContent value='server'>
        <ProvidersPanel scope='server' />
      </TabsContent>
    </Tabs>
  )
}
