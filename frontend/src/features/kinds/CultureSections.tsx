import { Flag, FlaskConical, Music, Shirt } from 'lucide-react'
import { ConceptSection } from './ConceptSection'

export function DressSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  return (
    <ConceptSection
      id='section-dress'
      nodeId={nodeId}
      concepts={['garment', 'colour_term', 'scent']}
      title='Dress, colour and scent'
      description='What its folk wear, the colours they name and what those mean, and the scents they burn, wear and trade; warmth guards against the cold, fine dress meets sumptuary laws and fashion rises and fades.'
      icon={Shirt}
      tone='gold'
      readOnlyReason={readOnlyReason}
    />
  )
}

export function EmblemsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  return (
    <ConceptSection
      id='section-emblems'
      nodeId={nodeId}
      concepts={['emblem_system']}
      title='Emblems'
      description='How it marks its houses, realms, orders and faiths; legible emblems keep order in its towns, and arms are borne under heraldry.'
      icon={Flag}
      tone='info'
      readOnlyReason={readOnlyReason}
    />
  )
}

export function MusicSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  return (
    <ConceptSection
      id='section-music'
      nodeId={nodeId}
      concepts={['instrument', 'music_tradition']}
      title='Music'
      description='The instruments its folk play and the traditions they play in; music in rites and loud gatherings eases the unrest of its towns.'
      icon={Music}
      tone='verdigris'
      readOnlyReason={readOnlyReason}
    />
  )
}

export function SubstancesSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  return (
    <ConceptSection
      id='section-substances'
      nodeId={nodeId}
      concepts={['substance']}
      title='Substances'
      description='What its folk take to change body or mind; dependence breeds crime, harm lowers sanitation, rites ease unrest, makers earn from trade and a realm may forbid it.'
      icon={FlaskConical}
      tone='warning'
      readOnlyReason={readOnlyReason}
    />
  )
}
