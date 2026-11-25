import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const ROOT = path.resolve(import.meta.dirname, '..')
const SOURCE = process.argv[2] ? path.resolve(process.argv[2]) : path.join(ROOT, 'src')
const GATED_MODULE = path.join(ROOT, 'src', 'api', 'mutation.ts')
const WRITES = new Set(['POST', 'PATCH', 'PUT', 'DELETE'])
const HANDLER = /^(on[A-Z]\w*|handleConfirm)$/
const RECEIVER = /([A-Za-z_$][\w$]*(?:\??\.[A-Za-z_$][\w$]*)*)\??\.mutate(?:Async)?\(/g
const MUTATION_HOOK = /^(useMutation|useGodAction|libraryMutation|use[A-Z]\w*(Mutation|Action))$/
const COMPONENT = /^(use)?[A-Z]/
const GATED_HOOK = /^(useMutation|useGodAction|useLoreMutation|useCosmicAction)$/
const WRITE_CALL = /\bapi\.(POST|PUT|PATCH|DELETE)\(|\bpostAction\(/
const TRIGGER = /^(DialogTrigger|PopoverTrigger|DropdownMenuTrigger|SheetTrigger|AlertDialogTrigger|CollapsibleTrigger)$/
const MAKES_MUTATION = /\b(useGodAction|useMutation|useLoreMutation|useCosmicAction|use[A-Z]\w*Action)\(/
const HOLD_CONTROL = /^(Switch|SwitchField|SwitchToggle)$/
const HOLD_VALUE = /^\{[\w.?]*[hH]old\b/

function sourceFiles(dir) {
  const found = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      if (entry.name !== 'generated') found.push(...sourceFiles(full))
    } else if (/\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name)) {
      found.push(full)
    }
  }
  return found
}

function receivers(text) {
  const found = new Set()
  for (const match of text.matchAll(RECEIVER)) found.add(match[1].replace(/\?\./g, '.'))
  return found
}

function actNames(attribute) {
  if (!attribute.initializer) return new Set()
  return new Set(
    attribute.initializer
      .getText()
      .replace(/^\{|\}$/g, '')
      .replace(/\.flat\(\)/g, '')
      .split(/[\s,[\]]+/)
      .filter(Boolean)
  )
}

function scopeOf(node) {
  let current = node.parent
  while (current && !ts.isBlock(current) && !ts.isSourceFile(current)) current = current.parent
  return current
}

function localFunctions(sf) {
  const fns = []
  ;(function collect(node) {
    if (
      ts.isVariableDeclaration(node) &&
      node.initializer &&
      ts.isIdentifier(node.name) &&
      (ts.isArrowFunction(node.initializer) || ts.isFunctionExpression(node.initializer))
    )
      fns.push({ name: node.name.text, fn: node.initializer, scope: scopeOf(node) })
    if (ts.isFunctionDeclaration(node) && node.name && !COMPONENT.test(node.name.text))
      fns.push({ name: node.name.text, fn: node, scope: scopeOf(node) })
    ts.forEachChild(node, collect)
  })(sf)
  return fns
}

function visibleFunctions(fns, node) {
  return fns.filter(({ scope }) => scope && node.pos >= scope.pos && node.end <= scope.end)
}

function fired(attribute, fns, sf) {
  const found = new Set()
  if (!HANDLER.test(attribute.name.getText(sf)) || !attribute.initializer) return found
  const handler = attribute.initializer.getText(sf)
  for (const name of receivers(handler)) found.add(name)
  for (const { name, fn } of visibleFunctions(fns, attribute)) {
    if (!new RegExp(`(^|[^.\\w$])${name}\\b`).test(handler)) continue
    const params = new Set((fn.parameters ?? []).map((param) => param.name.getText(sf)))
    for (const name of receivers(fn.getText(sf))) if (!params.has(name.split('.')[0])) found.add(name)
  }
  return found
}

function submitButtonsHaveAct(form, sf, wanted) {
  let ok = false
  ;(function visit(node) {
    if ((ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) && node.tagName.getText(sf) !== 'form') {
      const attrs = node.attributes.properties.filter(ts.isJsxAttribute)
      const act = attrs.find((a) => a.name.getText(sf) === 'act')
      if (act && [...wanted].every((name) => actNames(act).has(name))) ok = true
    }
    ts.forEachChild(node, visit)
  })(componentOf(form))
  return ok
}

function componentOf(node) {
  let current = node.parent
  while (current.parent && !(ts.isFunctionDeclaration(current) || ts.isArrowFunction(current) || ts.isFunctionExpression(current)))
    current = current.parent
  return current
}

function discarded(call) {
  let node = call
  while (node.parent) {
    const parent = node.parent
    if (ts.isReturnStatement(parent) || (ts.isArrowFunction(parent) && parent.body === node)) return false
    if (ts.isVariableDeclaration(parent) || ts.isPropertyAssignment(parent) || ts.isJsxExpression(parent)) return false
    if (ts.isVoidExpression(parent) || ts.isExpressionStatement(parent)) return true
    if (ts.isBlock(parent) || ts.isSourceFile(parent)) return false
    node = parent
  }
  return false
}

function guarded(call) {
  let node = call.parent
  let inComponent = false
  while (node) {
    if (ts.isCallExpression(node)) {
      const callee = node.expression
      if (MUTATION_HOOK.test(callee.getText())) return true
      if (ts.isPropertyAccessExpression(callee) && /^mutate(Async)?$/.test(callee.name.text)) return true
    }
    if (ts.isFunctionDeclaration(node) && node.name && COMPONENT.test(node.name.text)) inComponent = true
    if (
      ts.isVariableDeclaration(node) &&
      COMPONENT.test(node.name.getText()) &&
      node.initializer &&
      (ts.isArrowFunction(node.initializer) || ts.isFunctionExpression(node.initializer))
    )
      inComponent = true
    node = node.parent
  }
  return !inComponent || !discarded(call)
}


function collapsibleActs(trigger, sf) {
  let holder = trigger.parent
  while (holder && !(ts.isJsxElement(holder) && /Collapsible$/.test(holder.openingElement.tagName.getText(sf)))) holder = holder.parent
  if (!holder) return true
  const content = holder.children.find(
    (child) => ts.isJsxElement(child) && child.openingElement.tagName.getText(sf) === 'CollapsibleContent'
  )
  if (!content) return true
  const text = content.getText(sf)
  return /\bact=\{|\.mutate(Async)?\(|<form\b|onSubmit=|<[A-Z]\w*Form\b/.test(text) || rendersActing(text)
}

let ACTING = new Set()

function actingComponents(sf) {
  const found = new Set()
  for (const statement of sf.statements) {
    if (ts.isFunctionDeclaration(statement) && statement.name && /^[A-Z]/.test(statement.name.text)) {
      if (/\bact=\{|\.mutate(Async)?\(|\buse(GodAction|LoreMutation|Mutation)\(/.test(statement.getText(sf))) found.add(statement.name.text)
    }
  }
  return found
}

function rendersActing(text) {
  for (const match of text.matchAll(/<([A-Z][\w$]*)\b/g)) if (ACTING.has(match[1])) return true
  return false
}

const DIALOG = /^(ConfirmDialog|Dialog|AlertDialog|Sheet)$/
const OPENS = /\bset([A-Z][\w$]*)\(\s*(?:true\b|'[^']+'|\{|!|\(?\w+\)?\s*=>\s*!|[\w.]+\s*===\s*'[^']+'\s*\?\s*null\s*:\s*'|[\w.]+\s*\?\s*null\s*:)/g

function outerComponent(node) {
  let found = node
  let current = node.parent
  while (current && !ts.isSourceFile(current)) {
    if (ts.isFunctionDeclaration(current) || ts.isArrowFunction(current) || ts.isFunctionExpression(current)) found = current
    current = current.parent
  }
  return found
}

function openedStates(attribute, fns, sf) {
  const handler = attribute.initializer?.getText(sf) ?? ''
  const bodies = [handler]
  for (const { name, fn } of visibleFunctions(fns, attribute))
    if (new RegExp(`(^|[^.\\w$])${name}\\b`).test(handler)) bodies.push(fn.getText(sf))
  const states = new Set()
  for (const body of bodies) for (const match of body.matchAll(OPENS)) states.add(match[1][0].toLowerCase() + match[1].slice(1))
  return states
}

function actingDialogs(owner, sf) {
  const found = new Map()
  ;(function walk(node) {
    if ((ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node))) {
      const opening = ts.isJsxElement(node) ? node.openingElement : node
      if (DIALOG.test(opening.tagName.getText(sf))) {
        const open = opening.attributes.properties.find((a) => ts.isJsxAttribute(a) && a.name.getText(sf) === 'open')
        const text = node.getText(sf)
        const acts = /\bact=\{/.test(text) || receivers(text).length > 0
        if (open && acts)
          for (const match of (open.initializer?.getText(sf) ?? '').matchAll(/[A-Za-z_$][\w$]*/g)) found.set(match[0], opening.tagName.getText(sf))
      }
    }
    if (
      ts.isJsxExpression(node) &&
      node.expression &&
      ts.isBinaryExpression(node.expression) &&
      node.expression.operatorToken.kind === ts.SyntaxKind.AmpersandAmpersandToken
    ) {
      const shown = node.expression.right.getText(sf)
      if (/\bact=\{/.test(shown) || receivers(shown).size > 0 || rendersActing(shown))
        for (const match of node.expression.left.getText(sf).matchAll(/[A-Za-z_$][\w$]*/g)) found.set(match[0], 'inline form')
    }
    if (ts.isJsxExpression(node) && node.expression && ts.isConditionalExpression(node.expression)) {
      const shown = node.expression.whenTrue.getText(sf)
      if (/\bact=\{/.test(shown) || receivers(shown).size > 0 || rendersActing(shown))
        for (const match of node.expression.condition.getText(sf).matchAll(/[A-Za-z_$][\w$]*/g)) found.set(match[0], 'inline form')
    }
    ts.forEachChild(node, walk)
  })(owner)
  return found
}

function writerFunctions(dir) {
  const names = new Set(['postAction'])
  for (const file of sourceFiles(dir)) {
    const text = fs.readFileSync(file, 'utf8')
    for (const match of text.matchAll(/export (?:async )?function (\w+)\([^]*?\n\}/g))
      if (/\bapi\.(POST|PUT|PATCH|DELETE)\(/.test(match[0])) names.add(match[1])
  }
  return names
}

const WRITERS = writerFunctions(SOURCE)
const writesAnything = (text) =>
  WRITE_CALL.test(text) || [...WRITERS].some((name) => new RegExp(`\\b${name}\\(`).test(text))

const problems = []
for (const file of sourceFiles(SOURCE)) {
  const text = fs.readFileSync(file, 'utf8')
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS)
  ACTING = actingComponents(sf)
  const where = (node) => `${path.relative(ROOT, file)}:${sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1}`
  const fns = localFunctions(sf)
  ;(function visit(node) {
    if (
      ts.isImportDeclaration(node) &&
      node.moduleSpecifier.getText(sf) === "'@tanstack/react-query'" &&
      file !== GATED_MODULE &&
      /\buseMutation\b/.test(node.importClause?.getText(sf) ?? '')
    )
      problems.push(`${where(node)}: import useMutation from '@/api/mutation', which refuses acts the person's role does not allow`)
    if (ts.isJsxElement(node) && TRIGGER.test(node.openingElement.tagName.getText(sf))) {
      const child = node.children.find((c) => ts.isJsxElement(c) || ts.isJsxSelfClosingElement(c))
      const opening = child && (ts.isJsxElement(child) ? child.openingElement : child)
      const gated =
        opening &&
        opening.attributes.properties.some((a) => ts.isJsxAttribute(a) && /^(act|disabled)$/.test(a.name.getText(sf)))
      const owner = componentOf(node)
      const reveals = node.openingElement.tagName.getText(sf) !== 'CollapsibleTrigger' || collapsibleActs(node, sf)
      if (opening && !gated && reveals && MAKES_MUTATION.test(owner.getText(sf)))
        problems.push(`${where(node)}: <${node.openingElement.tagName.getText(sf)}> opens a place to act but its trigger has no act={…}, so a refused person opens it for nothing`)
    }
    if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
      const attrs = node.attributes.properties.filter(ts.isJsxAttribute)
      const checked = attrs.find((a) => a.name.getText(sf) === 'checked')
      if (
        HOLD_CONTROL.test(node.tagName.getText(sf)) &&
        checked &&
        HOLD_VALUE.test(checked.initializer?.getText(sf) ?? '') &&
        !attrs.some(
          (a) =>
            a.name.getText(sf) === 'permission' &&
            /lock_canon/.test(a.initializer?.getText(sf) ?? '')
        )
      )
        problems.push(`${where(node)}: a hold switch needs permission='lock_canon', so a person who may not lock canon sees it off with the reason`)
      const click = attrs.find((a) => a.name.getText(sf) === 'onClick')
      if (click && !attrs.some((a) => a.name.getText(sf) === 'act')) {
        const states = openedStates(click, fns, sf)
        if (states.size > 0) {
          const dialogs = actingDialogs(outerComponent(node), sf)
          const opens = [...states].filter((state) => dialogs.has(state))
          if (opens.length > 0)
            problems.push(`${where(node)}: <${node.tagName.getText(sf)}> opens a${dialogs.get(opens[0]) === 'inline form' ? 'n inline form' : ` <${dialogs.get(opens[0])}>`} that acts, but has no act={…}, so a refused person opens it for nothing`)
        }
      }
      const wanted = new Set()
      for (const attribute of attrs) for (const name of fired(attribute, fns, sf)) wanted.add(name)
      if (wanted.size > 0) {
        if (node.tagName.getText(sf) === 'form') {
          if (!submitButtonsHaveAct(node, sf, wanted))
            problems.push(`${where(node)}: the form that fires ${[...wanted].join(', ')} needs a control with act={…}`)
        } else {
          const names = new Set(
            attrs.filter((a) => /^acts?$/.test(a.name.getText(sf))).flatMap((a) => [...actNames(a)])
          )
          const stated = attrs
            .filter((a) => /^(disabled|aria-disabled)$/.test(a.name.getText(sf)))
            .map((a) => a.initializer?.getText(sf) ?? '')
            .join(' ')
          const missing = [...wanted].filter(
            (name) => !names.has(name) && !stated.includes(`${name}.blockedReason`)
          )
          if (missing.length > 0)
            problems.push(`${where(node)}: <${node.tagName.getText(sf)}> fires ${missing.join(', ')} without act={…}, so a refused person sees no reason`)
        }
      }
    }
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      GATED_HOOK.test(node.expression.text) &&
      node.arguments[0] &&
      ts.isObjectLiteralExpression(node.arguments[0])
    ) {
      const options = node.arguments[0]
      const named = options.properties.some((p) => p.name && /^(writes|permission)$/.test(p.name.getText(sf)))
      const run = options.properties.find((p) => p.name && /^(run|mutationFn)$/.test(p.name.getText(sf)))
      if (!named && run && writesAnything(run.getText(sf)))
        problems.push(`${where(node)}: ${node.expression.text} writes without naming it in writes: […], so the team gate cannot refuse it`)
      const value = run && ts.isPropertyAssignment(run) ? run.initializer : null
      if (!named && value && (ts.isIdentifier(value) || ts.isPropertyAccessExpression(value)) && file !== GATED_MODULE)
        problems.push(`${where(node)}: ${node.expression.text} runs ${value.getText(sf)}, whose writes the gate cannot see; name them in writes: […] or set permission`)
    }
    if (ts.isPropertyAssignment(node) && node.name.getText(sf) === 'busy') {
      const value = node.initializer.getText(sf)
      const pending = [...value.matchAll(/([A-Za-z_$][\w$]*)\.isPending/g)].map((match) => match[1])
      const unexplained = [...new Set(pending)].filter((name) => !value.includes(`${name}.blockedReason`))
      if (unexplained.length > 0)
        problems.push(`${where(node)}: busy reads ${unexplained.join(', ')}.isPending but not its blockedReason, so a refused person sees the control enabled`)
    }
    if (
      ts.isCallExpression(node) &&
      ts.isPropertyAccessExpression(node.expression) &&
      WRITES.has(node.expression.name.text) &&
      node.expression.expression.getText(sf) === 'api' &&
      !guarded(node)
    )
      problems.push(`${where(node)}: a write fired and forgotten in a component escapes the team gate; send it through a gated mutation`)
    ts.forEachChild(node, visit)
  })(sf)
}

for (const problem of problems) console.log(problem)
console.log(`act gates: ${problems.length} problem(s)`)
process.exit(problems.length > 0 ? 1 : 0)
