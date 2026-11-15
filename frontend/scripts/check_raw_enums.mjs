import path from 'node:path'
import ts from 'typescript'

const ROOT = path.resolve(import.meta.dirname, '..')
const SOURCE = path.join(ROOT, 'src')
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
const program = ts.createProgram(parsed.fileNames, parsed.options)
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

function shownTemplate(template) {
  const holder = template.parent
  if (!ts.isJsxExpression(holder)) return false
  return ts.isJsxAttribute(holder.parent) ? shownAttribute(holder.parent) : true
}

for (const file of program.getSourceFiles()) {
  if (!file.fileName.startsWith(SOURCE) || file.fileName.includes('/generated/') || /\.test\.tsx?$/.test(file.fileName)) continue
  const visit = (node) => {
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
