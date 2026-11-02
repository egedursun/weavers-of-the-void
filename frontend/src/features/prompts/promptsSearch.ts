export const PROMPT_VIEWS = ['son', 'blocks', 'catalogue', 'motifs'] as const

export type PromptView = (typeof PROMPT_VIEWS)[number]

export type PromptsSearch = {
  son?: number
  view?: PromptView
}

function isPromptView(value: unknown): value is PromptView {
  return (
    typeof value === 'string' &&
    (PROMPT_VIEWS as readonly string[]).includes(value)
  )
}

export function validatePromptsSearch(
  search: Record<string, unknown>
): PromptsSearch {
  const son = Number(search.son)
  return {
    ...(Number.isInteger(son) && son > 0 ? { son } : {}),
    ...(isPromptView(search.view) ? { view: search.view } : {}),
  }
}
