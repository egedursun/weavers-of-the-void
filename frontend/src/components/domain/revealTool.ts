export const REVEAL_TOOL_EVENT = 'aerona:reveal-tool'

export function toolAnchor(tool: string): string {
  return `tool-${tool}`
}

export function revealTool(tool: string) {
  window.dispatchEvent(new CustomEvent(REVEAL_TOOL_EVENT, { detail: tool }))
  window.requestAnimationFrame(() =>
    window.requestAnimationFrame(() =>
      document
        .getElementById(toolAnchor(tool))
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    )
  )
}
