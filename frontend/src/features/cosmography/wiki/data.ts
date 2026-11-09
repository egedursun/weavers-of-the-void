import { useCosmography, useCosmographyCatalog, useScaleWiki } from '../api'
import { ladderOf } from '../ladder'

export function useScaleData(nodeId: number) {
  const view = useCosmography()
  const catalog = useCosmographyCatalog()
  const wiki = useScaleWiki(nodeId)
  return {
    view,
    catalog: catalog.data,
    wiki: wiki.data,
    ladder: view.data ? ladderOf(view.data) : null,
  }
}

export function pageId(id: string | undefined): number | null {
  const value = Number(id)
  return Number.isInteger(value) && value > 0 ? value : null
}
