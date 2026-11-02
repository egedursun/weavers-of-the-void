import { type DrawerPageProps } from '@/components/layout/drawer/DrawerStack'
import { EntityView } from './EntityView'
import { parseEntityId } from './parseEntityId'

export function EntityPage({ id }: DrawerPageProps) {
  return <EntityView id={parseEntityId(id)} />
}
