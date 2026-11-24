import path from 'node:path'
import ts from 'typescript'

const ROOT = path.resolve(import.meta.dirname, '..')
const LOOKUPS = new Set(['named', 'plain'])

const parsed = ts.getParsedCommandLineOfConfigFile(path.join(ROOT, 'tsconfig.app.json'), {}, {
  ...ts.sys,
  onUnRecoverableConfigFileDiagnostic: (diagnostic) => {
    throw new Error(ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n'))
  },
})
const program = ts.createProgram(parsed.fileNames, parsed.options)
const checker = program.getTypeChecker()

function unwrapped(node) {
  let current = node
  while (ts.isParenthesizedExpression(current) || ts.isNonNullExpression(current) || ts.isAsExpression(current) || ts.isSatisfiesExpression(current))
    current = current.expression
  return current
}

function members(type) {
  const parts = type.isUnion() ? type.types : [type]
  const found = []
  for (const part of parts) {
    if (part.flags & (ts.TypeFlags.Null | ts.TypeFlags.Undefined)) continue
    if (!part.isStringLiteral()) return []
    found.push(part.value)
  }
  return found.length > 1 ? found : []
}

function tableKeys(node) {
  const target = unwrapped(node)
  if (!ts.isIdentifier(target)) return null
  let symbol = checker.getSymbolAtLocation(target)
  if (symbol && symbol.flags & ts.SymbolFlags.Alias) symbol = checker.getAliasedSymbol(symbol)
  const declaration = symbol?.valueDeclaration
  if (!declaration || !ts.isVariableDeclaration(declaration) || !declaration.initializer) return null
  const statement = declaration.parent?.parent
  if (!statement || !ts.isVariableStatement(statement) || !ts.isSourceFile(statement.parent)) return null
  if (!(declaration.parent.flags & ts.NodeFlags.Const)) return null
  const literal = unwrapped(declaration.initializer)
  if (!ts.isObjectLiteralExpression(literal)) return null
  const names = []
  for (const property of literal.properties) {
    if (!ts.isPropertyAssignment(property) && !ts.isShorthandPropertyAssignment(property)) return null
    const name = property.name
    if (ts.isIdentifier(name) || ts.isStringLiteral(name)) names.push(name.text)
    else return null
  }
  return names.length > 0 ? { name: target.text, names } : null
}

const found = []

function check(table, key, file, node) {
  const keys = tableKeys(table)
  if (!keys) return
  const values = members(checker.getTypeAtLocation(unwrapped(key)))
  if (values.length === 0) return
  if (keys.names.some((name) => values.includes(name))) return
  const { line } = file.getLineAndCharacterOfPosition(node.getStart())
  found.push(
    `${path.relative(ROOT, file.fileName)}:${line + 1} looks up ${keys.name} by ${unwrapped(key).getText()} (${values.slice(0, 3).join(', ')}…), but ${keys.name} names none of those values (${keys.names.slice(0, 3).join(', ')}…); key the map by the enum`
  )
}

for (const file of program.getSourceFiles()) {
  if (file.isDeclarationFile || !file.fileName.startsWith(path.join(ROOT, 'src'))) continue
  if (/\.test\.tsx?$/.test(file.fileName) || file.fileName.includes(`${path.sep}generated${path.sep}`)) continue
  const visit = (node) => {
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && LOOKUPS.has(node.expression.text) && node.arguments.length >= 2)
      check(node.arguments[0], node.arguments[1], file, node)
    if (ts.isElementAccessExpression(node)) check(node.expression, node.argumentExpression, file, node)
    ts.forEachChild(node, visit)
  }
  visit(file)
}

if (found.length > 0) {
  console.error(found.join('\n'))
  console.error(`\n${found.length} label lookups use a map keyed by other words than the enum they are given.`)
  process.exit(1)
}
console.log('every label lookup uses a map keyed by its enum')
