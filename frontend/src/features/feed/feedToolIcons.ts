import {
  BookOpen,
  Brain,
  Eye,
  Gift,
  Hammer,
  HandHelping,
  Languages,
  type LucideIcon,
  Skull,
  Star,
  Swords,
  Users,
  Wrench,
} from 'lucide-react'
import { toolIdIcon } from '@/components/domain/toolIcons'

const TOOL_ICON_RULES: readonly (readonly [RegExp, LucideIcon])[] = [
  [/^(read|look|inspect|list|get|see|view|check|search|find)/, Eye],
  [/(memory|remember|forget|recall|note|plan)/, Brain],
  [/(language|word|speech|name)/, Languages],
  [/(war|army|battle|fight|raid|siege)/, Swords],
  [/(death|kill|resurrect|curse|ruin|destroy)/, Skull],
  [/(pray|answer|bless|forgive)/, HandHelping],
  [/(gift|trade|barter|lend|repay|coin|resource)/, Gift],
  [/(sibling|kin|bond|child|family|adopt|marry)/, Users],
  [/(star|cosmos|world|sky|gate|route|voyage)/, Star],
  [/(chronicle|epic|write|story|book)/, BookOpen],
  [/(create|build|make|found|forge|weave)/, Hammer],
]

export function toolIcon(tool: string | null): LucideIcon {
  if (!tool) return Wrench
  const known = toolIdIcon(tool)
  if (known) return known
  const match = TOOL_ICON_RULES.find(([pattern]) => pattern.test(tool))
  return match ? match[1] : Wrench
}

export function toolLabel(tool: string | null): string {
  if (!tool) return 'a tool'
  const spaced = tool.replace(/[_:]+/g, ' ').trim()
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}
