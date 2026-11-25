import { Link } from '@tanstack/react-router'
import { Speech } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { type EntryRef } from '@/components/layout/entry/entryStack'
import { useSpeaker } from './api'

const SPEAKING_KINDS: ReadonlySet<EntryRef['kind']> = new Set([
  'son',
  'foreign-god',
  'entity',
])

function speakerId(entry: EntryRef): number | null {
  if (!SPEAKING_KINDS.has(entry.kind) || entry.id === undefined) return null
  const id = Number(entry.id)
  return Number.isInteger(id) && id > 0 ? id : null
}

export function SpeakWithThem({ entry }: { entry: EntryRef }) {
  const nodeId = speakerId(entry)
  const speaker = useSpeaker(nodeId)
  if (nodeId === null || !speaker.data) return null
  return (
    <Button
      variant='outline'
      size='sm'
      asChild
      title={`Summon ${speaker.data.card.name} to presence and speak with it`}
    >
      <Link to='/presence' search={{ node: nodeId }}>
        <Speech />
        <span className='max-sm:sr-only'>Speak with them</span>
      </Link>
    </Button>
  )
}
