import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const ROOT = path.resolve(import.meta.dirname, '..')
const SOURCE = process.argv[2] ? path.resolve(process.argv[2]) : path.join(ROOT, 'src', 'features')
const BARE = new Set(['StatBar'])
const FRAMED = new Set(['MiniStat'])
const TILE_SURFACE = /(^|\s)surface-(sheen|framed)(\s|$)/

function sourceFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name)
    if (entry.isDirectory()) return sourceFiles(full)
    return entry.name.endsWith('.tsx') && !entry.name.endsWith('.test.tsx') ? [full] : []
  })
}

function tagName(node) {
  return (ts.isJsxElement(node) ? node.openingElement.tagName : node.tagName).getText()
}

function classText(node) {
  const attributes = ts.isJsxElement(node) ? node.openingElement.attributes : node.attributes
  const parts = []
  for (const attribute of attributes.properties) {
    if (!ts.isJsxAttribute(attribute) || attribute.name.getText() !== 'className') continue
    const visit = (child) => {
      if (ts.isStringLiteralLike(child)) parts.push(child.text)
      ts.forEachChild(child, visit)
    }
    if (attribute.initializer) visit(attribute.initializer)
  }
  return parts.join(' ')
}

function framedProp(node) {
  const attributes = ts.isJsxElement(node) ? node.openingElement.attributes : node.attributes
  return attributes.properties.some(
    (attribute) =>
      ts.isJsxAttribute(attribute) &&
      attribute.name.getText() === 'framed' &&
      (!attribute.initializer || attribute.initializer.getText() !== '{false}')
  )
}

function face(node) {
  const name = tagName(node)
  if (BARE.has(name)) return framedProp(node) ? `framed ${name}` : `bare ${name}`
  if (FRAMED.has(name)) return `framed ${name}`
  if (!/^[a-z]/.test(name)) return null
  if (TILE_SURFACE.test(classText(node))) return `framed <${name}> tile`
  if (!ts.isJsxElement(node)) return null
  const inner = rendered([...node.children]).map(face).filter(Boolean)
  if (inner.length === 0) return null
  if (inner.every((item) => item.startsWith('bare'))) return inner[0]
  if (inner.every((item) => item.startsWith('framed'))) return inner[0]
  return null
}

function returned(fn) {
  if (!ts.isArrowFunction(fn) && !ts.isFunctionExpression(fn)) return []
  if (!ts.isBlock(fn.body)) return [fn.body]
  const found = []
  const visit = (node) => {
    if (ts.isReturnStatement(node) && node.expression) found.push(node.expression)
    else if (!ts.isFunctionLike(node)) ts.forEachChild(node, visit)
  }
  visit(fn.body)
  return found
}

function rendered(children) {
  const found = []
  const take = (node) => {
    if (ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node)) found.push(node)
    else if (ts.isJsxFragment(node)) node.children.forEach(take)
    else if (ts.isJsxExpression(node) && node.expression) take(node.expression)
    else if (ts.isBinaryExpression(node)) take(node.right)
    else if (ts.isConditionalExpression(node)) {
      take(node.whenTrue)
      take(node.whenFalse)
    } else if (ts.isParenthesizedExpression(node)) take(node.expression)
    else if (ts.isCallExpression(node) && node.arguments.length > 0)
      returned(node.arguments[0]).forEach(take)
  }
  children.forEach(take)
  return found
}

const problems = []
for (const file of sourceFiles(SOURCE)) {
  const text = fs.readFileSync(file, 'utf8')
  if (!text.includes('StatBar')) continue
  const source = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  const visit = (node) => {
    if (ts.isJsxElement(node)) {
      const faces = new Set(rendered([...node.children]).map(face).filter(Boolean))
      const bare = [...faces].filter((item) => item.startsWith('bare'))
      const framed = [...faces].filter((item) => item.startsWith('framed'))
      if (bare.length > 0 && framed.length > 0) {
        const { line } = source.getLineAndCharacterOfPosition(node.getStart())
        problems.push(
          `${path.relative(ROOT, file)}:${line + 1} lays a ${bare.join(', ')} beside a ${framed.join(', ')}; frame every value the same way`
        )
      }
    }
    ts.forEachChild(node, visit)
  }
  visit(source)
}

const FIELD_CONTROLS = new Set(['Input', 'RecordCombobox', 'Textarea', 'SelectTrigger', 'MultiSelect', 'Select', 'Switch', 'Slider'])
const SRC = path.join(ROOT, 'src')
const parsed = new Map(
  [...new Set([...sourceFiles(SRC), ...sourceFiles(SOURCE)])].map((file) => [file, ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)])
)
const fieldFaces = new Map()
for (const [file, source] of parsed) {
  for (const statement of source.statements) {
    if (!ts.isFunctionDeclaration(statement) || !statement.name || !/(Field|Picker)$/.test(statement.name.text)) continue
    let control = false
    let framed = false
    const visit = (node) => {
      if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
        const tag = node.tagName.getText()
        if (FIELD_CONTROLS.has(tag)) control = true
        if (tag === 'FieldTile') framed = true
      }
      if (ts.isStringLiteralLike(node) && /surface-(framed|sheen)/.test(node.text)) framed = true
      ts.forEachChild(node, visit)
    }
    visit(statement)
    if (control) fieldFaces.set(`${file}#${statement.name.text}`, framed ? 'framed' : 'bare')
  }
}

const LABELS = new Set(['Label', 'FieldLabel'])

function unframedProp(element) {
  return element.attributes.properties.some(
    (attribute) => ts.isJsxAttribute(attribute) && attribute.name.getText() === 'framed' && attribute.initializer?.getText() === '{false}'
  )
}

function inlineFace(node) {
  const element = ts.isJsxElement(node) ? node.openingElement : node
  const tag = element.tagName.getText()
  if (tag === 'FieldTile') return unframedProp(element) ? 'bare' : 'framed'
  if (FIELD_CONTROLS.has(tag) && tag !== 'Select') return 'bare'
  if (!/^[a-z]/.test(tag) || !ts.isJsxElement(node)) return undefined
  const inner = rendered([...node.children]).map((child) => (ts.isJsxElement(child) ? child.openingElement : child).tagName.getText())
  if (!inner.some((name) => LABELS.has(name)) || !inner.some((name) => FIELD_CONTROLS.has(name))) return undefined
  return TILE_SURFACE.test(classText(node)) ? 'framed' : 'bare'
}

function moduleFile(from, specifier) {
  const base = specifier.startsWith('@/') ? path.join(SRC, specifier.slice(2)) : specifier.startsWith('.') ? path.resolve(path.dirname(from), specifier) : null
  if (!base) return null
  return [`${base}.tsx`, path.join(base, 'index.tsx')].find((candidate) => parsed.has(candidate)) ?? null
}

for (const [file, source] of parsed) {
  if (!file.startsWith(SOURCE)) continue
  const fields = new Map()
  for (const statement of source.statements) {
    if (ts.isImportDeclaration(statement) && statement.importClause?.namedBindings && ts.isNamedImports(statement.importClause.namedBindings)) {
      const target = moduleFile(file, statement.moduleSpecifier.text)
      if (!target) continue
      for (const element of statement.importClause.namedBindings.elements) {
        const faceOf = fieldFaces.get(`${target}#${(element.propertyName ?? element.name).text}`)
        if (faceOf) fields.set(element.name.text, faceOf)
      }
    }
    if (ts.isFunctionDeclaration(statement) && statement.name) {
      const faceOf = fieldFaces.get(`${file}#${statement.name.text}`)
      if (faceOf) fields.set(statement.name.text, faceOf)
    }
  }
  const visit = (node) => {
    if (ts.isJsxElement(node)) {
      const bare = new Set()
      const framed = new Set()
      for (const child of rendered([...node.children])) {
        const element = ts.isJsxElement(child) ? child.openingElement : child
        const tag = element.tagName.getText()
        const faceOf = fields.get(tag) ?? inlineFace(child)
        if (!faceOf) continue
        const unframed = element.attributes.properties.some(
          (attribute) => ts.isJsxAttribute(attribute) && attribute.name.getText() === 'framed' && attribute.initializer?.getText() === '{false}'
        )
        ;(faceOf === 'bare' || unframed ? bare : framed).add(tag)
      }
      if (bare.size > 0 && framed.size > 0) {
        const { line } = source.getLineAndCharacterOfPosition(node.getStart())
        problems.push(
          `${path.relative(ROOT, file)}:${line + 1} lays a bare ${[...bare].join(', ')} field beside a framed ${[...framed].join(', ')} field; frame every field the same way`
        )
      }
    }
    ts.forEachChild(node, visit)
  }
  visit(source)
}

const GROUP_CONTROLS = new Set([...FIELD_CONTROLS, 'Checkbox', 'RadioGroup', 'ToggleGroup'])
const HIDDEN_LABEL = /(^|\s)sr-only(\s|$)/

function tagOfNode(node) {
  return (ts.isJsxElement(node) ? node.openingElement : node).tagName.getText()
}

function framedElement(node) {
  return tagOfNode(node) === 'FieldTile' || TILE_SURFACE.test(classText(node))
}

function holdsBareControl(node, depth) {
  if (framedElement(node)) return false
  if (GROUP_CONTROLS.has(tagOfNode(node))) return true
  if (depth <= 0 || !ts.isJsxElement(node)) return false
  return rendered([...node.children]).some((child) => holdsBareControl(child, depth - 1))
}

function namesControl(label) {
  const element = ts.isJsxElement(label) ? label.openingElement : label
  return element.attributes.properties.some((attribute) => ts.isJsxAttribute(attribute) && attribute.name.getText() === 'htmlFor')
}

for (const [file, source] of parsed) {
  if (file.includes(`${path.sep}components${path.sep}ui${path.sep}`) || file.endsWith('FieldTile.tsx')) continue
  if (!file.startsWith(SRC) && !file.startsWith(SOURCE)) continue
  const visit = (node) => {
    if (ts.isJsxElement(node) && !framedElement(node) && tagOfNode(node) !== 'li') {
      const kids = node.children.filter((child) => ts.isJsxElement(child) || ts.isJsxSelfClosingElement(child))
      const label = kids.find((child) => LABELS.has(tagOfNode(child)) && !HIDDEN_LABEL.test(classText(child)))
      const reach = label && namesControl(label) ? 3 : 1
      if (label && kids.some((child) => child !== label && holdsBareControl(child, reach))) {
        const { line } = source.getLineAndCharacterOfPosition(node.getStart())
        problems.push(`${path.relative(ROOT, file)}:${line + 1} holds a labelled control outside a frame; put the label and its control in a FieldTile`)
      }
    }
    ts.forEachChild(node, visit)
  }
  visit(source)
}

for (const problem of problems) console.log(problem)
console.log(`value frames: ${problems.length}`)
process.exit(problems.length > 0 ? 1 : 0)
