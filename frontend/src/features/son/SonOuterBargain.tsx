import { Section } from '@/components/domain'
import { type SonRecord } from '@/features/pantheon/api'
import { OuterBargainForm } from './OuterBargainForm'

export function SonOuterBargain({ son }: { son: SonRecord }) {
  return (
    <Section
      id='section-son-bargains'
      title='Bargains with the outside'
      description={`Make ${son.name} strike a bargain with a thing beyond the stars, or forbid them to.`}
      level={3}
    >
      <OuterBargainForm sons={[son]} fixedSonId={son.id} />
    </Section>
  )
}
