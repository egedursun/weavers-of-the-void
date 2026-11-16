import { useState } from 'react'
import { Blocks, BookText, Crown, Repeat } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { IntroNote } from '@/components/domain'
import { ContextBlocksView } from './ContextBlocksView'
import { PromptCatalogueView } from './PromptCatalogueView'
import { SonPromptView } from './SonPromptView'
import { TiredMotifsView } from './TiredMotifsView'
import { type PromptView, type PromptsSearch } from './promptsSearch'

type PromptsPageProps = {
  search?: PromptsSearch
}

export function PromptsPage({ search = {} }: PromptsPageProps) {
  const [view, setView] = useState<PromptView>(search.view ?? 'son')
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <IntroNote>
        Look at exactly what the agents read: a son’s whole turn prompt, every
        context block, the prompt catalogue with its templates, and the motifs
        Fate holds back.
      </IntroNote>
      <Tabs
        value={view}
        onValueChange={(value) => setView(value as PromptView)}
        className='flex min-w-0 flex-col gap-6'
      >
        <TabsList aria-label='Prompt views' className='w-full md:w-fit'>
          <TabsTrigger value='son'>
            <Crown />
            Son prompt
          </TabsTrigger>
          <TabsTrigger value='blocks'>
            <Blocks />
            Context blocks
          </TabsTrigger>
          <TabsTrigger value='catalogue'>
            <BookText />
            Catalogue
          </TabsTrigger>
          <TabsTrigger value='motifs'>
            <Repeat />
            Tired motifs
          </TabsTrigger>
        </TabsList>
        <TabsContent value='son'>
          <SonPromptView initialSon={search.son ?? null} />
        </TabsContent>
        <TabsContent value='blocks'>
          <ContextBlocksView />
        </TabsContent>
        <TabsContent value='catalogue'>
          <PromptCatalogueView />
        </TabsContent>
        <TabsContent value='motifs'>
          <TiredMotifsView />
        </TabsContent>
      </Tabs>
    </div>
  )
}
