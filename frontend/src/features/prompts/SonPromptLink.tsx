import { Link } from '@tanstack/react-router'
import { ScrollText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Section } from '@/components/domain'

type SonPromptLinkProps = {
  sonId: number
  name: string
}

export function SonPromptLink({ sonId, name }: SonPromptLinkProps) {
  return (
    <Section
      id='section-prompt'
      title='Prompt'
      description={`The exact system and turn prompt ${name} would read now, with his tools and budget.`}
      level={3}
      actions={
        <Button variant='outline' size='sm' asChild>
          <Link to='/settings/prompts' search={{ son: sonId, view: 'son' }}>
            <ScrollText />
            Open his prompt
          </Link>
        </Button>
      }
    >
      {null}
    </Section>
  )
}
