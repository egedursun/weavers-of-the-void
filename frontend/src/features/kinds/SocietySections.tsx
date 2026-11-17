import { Briefcase, Crown, Network } from 'lucide-react'
import { ConceptSection } from './ConceptSection'

export function WorkSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  return (
    <ConceptSection
      id='section-work-kinds'
      nodeId={nodeId}
      concepts={['profession']}
      title='Professions'
      description='The work its folk make a living by; earnings raise the prosperity of its towns, risky work harms those who do it and purity sets who may do it.'
      icon={Briefcase}
      tone='gold'
      readOnlyReason={readOnlyReason}
    />
  )
}

export function RankKindsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  return (
    <ConceptSection
      id='section-rank-kinds'
      nodeId={nodeId}
      concepts={['rank']}
      title='Ranks'
      description='The standings it recognises; what a rank grants and what it owes moves how content those who hold it are.'
      icon={Crown}
      tone='info'
      readOnlyReason={readOnlyReason}
    />
  )
}

export function OrganisationKindsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  return (
    <ConceptSection
      id='section-organisation-kinds'
      nodeId={nodeId}
      concepts={['organisation']}
      title='Forms of organisation'
      description='The forms its bodies take; a body drifts towards the cohesion, secrecy and repute of its form, and a form that is outlawed outlaws the body.'
      icon={Network}
      tone='verdigris'
      readOnlyReason={readOnlyReason}
    />
  )
}
