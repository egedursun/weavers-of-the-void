import { TypePage } from '@/features/city/TypePages'
import { parseTypeKey } from '@/features/city/typeKeys'
import { AtlasGroup } from './AtlasGroup'
import { AtlasHome } from './AtlasHome'
import { type AtlasNode } from './atlasModel'

type AtlasDetailProps = {
  selection: string | null
  group?: AtlasNode | null
  records: number
  kinds: number
  onSelect: (key: string) => void
}

export function AtlasDetail({
  selection,
  group = null,
  records,
  kinds,
  onSelect,
}: AtlasDetailProps) {
  const typed = parseTypeKey(selection)
  if (group) return <AtlasGroup node={group} onSelect={onSelect} />
  if (typed) return <TypePage selection={typed} />
  return <AtlasHome records={records} kinds={kinds} onSelect={onSelect} />
}
