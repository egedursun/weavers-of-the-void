import { type EntryPageProps } from '@/components/layout/entry/EntryWindow'
import { EntityView } from './EntityView'
import { parseEntityId } from './parseEntityId'

export function EntityPage({ id }: EntryPageProps) {
  return <EntityView id={parseEntityId(id)} />
}
