import path from 'node:path'
import ts from 'typescript'

import fs from 'node:fs'

const ROOT = path.resolve(import.meta.dirname, '..')
const EXTRA = process.argv[2] ? path.resolve(process.argv[2]) : null
const SOURCE = EXTRA ?? path.join(ROOT, 'src')
const DISPLAY = new Set([
  'alt',
  'aria',
  'aria-label',
  'badge',
  'caption',
  'description',
  'detail',
  'eyebrow',
  'heading',
  'hint',
  'label',
  'meta',
  'note',
  'placeholder',
  'reason',
  'sub',
  'subtitle',
  'summary',
  'text',
  'title',
  'tooltip',
])
const KEY = /^[a-z][a-z0-9]*(_[a-z0-9]+)*$/
const IDENTIFIER_STYLE = /\bfont-mono\b/

const parsed = ts.getParsedCommandLineOfConfigFile(path.join(ROOT, 'tsconfig.app.json'), {}, {
  ...ts.sys,
  onUnRecoverableConfigFileDiagnostic: (diagnostic) => {
    throw new Error(ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n'))
  },
})
const extraFiles = EXTRA
  ? fs.readdirSync(EXTRA).filter((name) => /\.tsx?$/.test(name)).map((name) => path.join(EXTRA, name))
  : []
const program = ts.createProgram([...parsed.fileNames, ...extraFiles], parsed.options)
const checker = program.getTypeChecker()

function keys(type) {
  const parts = type.isUnion() ? type.types : [type]
  const found = []
  for (const part of parts) {
    if (part.flags & (ts.TypeFlags.Null | ts.TypeFlags.Undefined)) continue
    if (!part.isStringLiteral() || !KEY.test(part.value)) return []
    found.push(part.value)
  }
  return found.length > 1 || found.some((value) => value.includes('_')) ? found : []
}

function unwrapped(node) {
  let current = node
  while (ts.isParenthesizedExpression(current) || ts.isNonNullExpression(current) || ts.isAsExpression(current)) current = current.expression
  return current
}

function authored(node) {
  if (!ts.isIdentifier(node)) return false
  const declaration = checker.getSymbolAtLocation(node)?.valueDeclaration
  const initializer = declaration && ts.isVariableDeclaration(declaration) ? declaration.initializer : undefined
  return initializer !== undefined && (ts.isConditionalExpression(initializer) || ts.isStringLiteralLike(initializer))
}

function styledAsIdentifier(node) {
  for (let current = node.parent; current; current = current.parent) {
    if (!ts.isJsxElement(current)) continue
    const name = current.openingElement.attributes.properties.find(
      (attribute) => ts.isJsxAttribute(attribute) && attribute.name.getText() === 'className'
    )
    if (name?.initializer && IDENTIFIER_STYLE.test(name.initializer.getText())) return true
  }
  return false
}

function shownAttribute(attribute) {
  const name = attribute.name.getText()
  return DISPLAY.has(name) || name.startsWith('aria-')
}

function labelledByReceiver(expression) {
  const expected = checker.getContextualType(expression)
  return expected !== undefined && keys(expected).length > 0
}

const found = []

function check(expression, file) {
  const node = unwrapped(expression)
  const reads = ts.isPropertyAccessExpression(node) || ts.isElementAccessExpression(node) || ts.isIdentifier(node) || ts.isCallExpression(node)
  if (!reads || authored(node) || styledAsIdentifier(node)) return
  const values = keys(checker.getTypeAtLocation(node))
  if (values.length === 0) return
  const { line } = file.getLineAndCharacterOfPosition(node.getStart())
  found.push(`${path.relative(ROOT, file.fileName)}:${line + 1} shows ${node.getText()} as a raw key (${values.slice(0, 3).join(', ')}…); show its label`)
}

const WORDING = new Set(['replace', 'replaceAll', 'split'])
const PASSING = new Set(['replace', 'replaceAll', 'toLowerCase', 'toUpperCase', 'trim', 'slice', 'substring'])

function splitsWords(argument) {
  if (argument === undefined) return false
  if (ts.isStringLiteralLike(argument)) return argument.text === '_'
  return ts.isRegularExpressionLiteral(argument) && /^\/[^/]*_[^/]*\/[a-z]*$/.test(argument.text)
}

function rootReceiver(expression) {
  let current = unwrapped(expression)
  while (
    ts.isCallExpression(current) &&
    ts.isPropertyAccessExpression(current.expression) &&
    PASSING.has(current.expression.name.text)
  )
    current = unwrapped(current.expression.expression)
  return current
}

function wordedByHand(node, file) {
  if (!ts.isPropertyAccessExpression(node.expression) || !WORDING.has(node.expression.name.text)) return
  if (!splitsWords(node.arguments[0])) return
  const spaced = node.arguments[1]
  if (node.expression.name.text !== 'split' && !(spaced && ts.isStringLiteralLike(spaced) && spaced.text === ' ')) return
  const receiver = rootReceiver(node.expression.expression)
  const values = keys(checker.getTypeAtLocation(receiver))
  if (values.length === 0) return
  const { line } = file.getLineAndCharacterOfPosition(node.getStart())
  found.push(
    `${path.relative(ROOT, file.fileName)}:${line + 1} words ${receiver.getText()} by hand (${values.slice(0, 3).join(', ')}…); show it through its label map`
  )
}

function wordingCall(node) {
  if (!ts.isCallExpression(node) || !ts.isPropertyAccessExpression(node.expression) || !WORDING.has(node.expression.name.text)) return null
  if (!splitsWords(node.arguments[0])) return null
  const spaced = node.arguments[1]
  if (node.expression.name.text !== 'split' && !(spaced && ts.isStringLiteralLike(spaced) && spaced.text === ' ')) return null
  return rootReceiver(node.expression.expression)
}

function functionOf(declaration) {
  if (!declaration) return null
  if (ts.isFunctionDeclaration(declaration)) return declaration
  if (ts.isVariableDeclaration(declaration) && declaration.initializer) {
    const value = unwrapped(declaration.initializer)
    if (ts.isArrowFunction(value) || ts.isFunctionExpression(value)) return value
  }
  return null
}

function calleeFunction(call) {
  const symbol = checker.getSymbolAtLocation(call.expression)
  const target = symbol && symbol.flags & ts.SymbolFlags.Alias ? checker.getAliasedSymbol(symbol) : symbol
  return functionOf(target?.valueDeclaration)
}

function parameterIndex(fn, expression) {
  if (!ts.isIdentifier(expression)) return -1
  const declaration = checker.getSymbolAtLocation(expression)?.valueDeclaration
  return declaration ? fn.parameters.indexOf(declaration) : -1
}

function namesParameter(identifier, index, fn) {
  if (parameterIndex(fn, identifier) === index) return true
  const declaration = checker.getSymbolAtLocation(identifier)?.valueDeclaration
  return Boolean(
    declaration &&
      ts.isVariableDeclaration(declaration) &&
      declaration.initializer &&
      parameterIndex(fn, rootReceiver(declaration.initializer)) === index
  )
}

function looksUp(node, index, fn) {
  let hit = false
  const visit = (child) => {
    if (ts.isIdentifier(child) && namesParameter(child, index, fn)) hit = true
    if (!hit) ts.forEachChild(child, visit)
  }
  visit(node)
  return hit
}

function fallback(node, index, fn) {
  for (let child = node, current = node.parent; current && current !== fn; child = current, current = current.parent) {
    const either =
      ts.isBinaryExpression(current) &&
      (current.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken || current.operatorToken.kind === ts.SyntaxKind.BarBarToken)
    if (either && current.right === child && looksUp(current.left, index, fn)) return true
    if (ts.isConditionalExpression(current) && current.whenFalse === child && looksUp(current.condition, index, fn)) return true
  }
  return false
}

const wordingParameters = new Map()

function wordsParameters(fn) {
  if (wordingParameters.has(fn)) return wordingParameters.get(fn)
  const indexes = new Set()
  wordingParameters.set(fn, indexes)
  const visit = (node) => {
    const receiver = wordingCall(node)
    if (receiver) {
      const index = parameterIndex(fn, receiver)
      if (index >= 0 && !fallback(node, index, fn)) indexes.add(index)
    }
    if (ts.isCallExpression(node)) {
      const inner = calleeFunction(node)
      if (inner && inner !== fn)
        for (const index of wordsParameters(inner))
          if (node.arguments[index]) {
            const passed = parameterIndex(fn, rootReceiver(node.arguments[index]))
            if (passed >= 0 && !fallback(node, passed, fn)) indexes.add(passed)
          }
    }
    ts.forEachChild(node, visit)
  }
  if (fn.body) visit(fn.body)
  return indexes
}

function wordedThroughHelper(node, file) {
  const fn = calleeFunction(node)
  if (!fn) return
  for (const index of wordsParameters(fn)) {
    const argument = node.arguments[index]
    if (!argument) continue
    const receiver = rootReceiver(argument)
    const values = keys(checker.getTypeAtLocation(receiver))
    if (values.length === 0) continue
    const { line } = file.getLineAndCharacterOfPosition(node.getStart())
    found.push(
      `${path.relative(ROOT, file.fileName)}:${line + 1} words ${receiver.getText()} by hand through ${node.expression.getText()} (${values.slice(0, 3).join(', ')}…); show it through its label map`
    )
  }
}

function shownTemplate(template) {
  const holder = template.parent
  if (!ts.isJsxExpression(holder)) return false
  return ts.isJsxAttribute(holder.parent) ? shownAttribute(holder.parent) : true
}

for (const file of program.getSourceFiles()) {
  if (!file.fileName.startsWith(SOURCE) || file.fileName.includes('/generated/') || /\.test\.tsx?$/.test(file.fileName)) continue
  const visit = (node) => {
    if (ts.isCallExpression(node)) {
      wordedByHand(node, file)
      wordedThroughHelper(node, file)
    }
    if (ts.isJsxExpression(node) && node.expression && (ts.isJsxElement(node.parent) || ts.isJsxFragment(node.parent))) check(node.expression, file)
    if (
      ts.isJsxAttribute(node) &&
      shownAttribute(node) &&
      node.initializer &&
      ts.isJsxExpression(node.initializer) &&
      node.initializer.expression &&
      !labelledByReceiver(node.initializer.expression)
    )
      check(node.initializer.expression, file)
    if (ts.isTemplateExpression(node) && shownTemplate(node)) for (const span of node.templateSpans) check(span.expression, file)
    ts.forEachChild(node, visit)
  }
  visit(file)
}

if (found.length > 0) {
  console.log(found.join('\n'))
  process.exit(1)
}
console.log('no raw enum keys on screen')
