import re
from pathlib import Path

UI = Path(__file__).resolve().parents[3] / "frontend" / "src" / "components" / "ui"
FUNCTION = re.compile(r"^function (\w+)\(([\s\S]*?)^\}$", re.M)
SIBLING = re.compile(r"\{children\}\s*\n\s*\{")


def unsafe(text: str) -> list[str]:
    found = []
    for match in FUNCTION.finditer(text):
        body = match.group(2)
        if "Primitive." not in body or not SIBLING.search(body):
            continue
        if "props.asChild ?" in body or ("Omit<React.ComponentProps<typeof" in body and "'asChild'>" in body):
            continue
        found.append(match.group(1))
    return found


def test_no_primitive_gets_a_sibling_beside_children_it_may_slot_onto() -> None:
    problems = [f"{path.name}: {name}" for path in sorted(UI.glob("*.tsx")) if ".test." not in path.name for name in unsafe(path.read_text(encoding="utf-8"))]
    assert problems == []


def test_the_rule_catches_a_sibling_after_slotted_children() -> None:
    bad = (
        "function Item({ children, ...props }: React.ComponentProps<typeof X.Item>) {\n"
        "  return (\n    <X.Item {...props}>\n      {children}\n      {note && <span />}\n    </X.Item>\n  )\n}\n"
    )
    good = bad.replace("{children}\n      {note && <span />}", "{props.asChild ? children : <>{children}{note && <span />}</>}")
    assert unsafe(bad.replace("X.Item", "XPrimitive.Item")) == ["Item"]
    assert unsafe(good.replace("X.Item", "XPrimitive.Item")) == []
