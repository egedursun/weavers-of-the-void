import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

UNPAGED = """
export function Writers({ link }) {
  return (
    <div className='flex min-w-0 flex-wrap gap-1.5'>
      {link.writers.map((key) => (
        <Badge key={key}>{key}</Badge>
      ))}
    </div>
  )
}
"""

PAGED = """
export function Writers({ link }) {
  const more = useShowMore(link.writers, 8)
  return (
    <div className='flex min-w-0 flex-wrap gap-1.5'>
      {more.visible.map((key) => (
        <Badge key={key}>{key}</Badge>
      ))}
    </div>
  )
}
"""

FIXED = """
export function Kinds() {
  return (
    <div className='flex min-w-0 flex-wrap gap-1.5'>
      {DIVINE_SCALES.map((key) => (
        <Badge key={key}>{key}</Badge>
      ))}
      {divineScaleValues.map((key) => (
        <Badge key={key}>{key}</Badge>
      ))}
    </div>
  )
}
"""

SCROLL_ONLY = """
export function Feed() {
  const { fetchNextPage, hasNextPage } = usePages()
  const loadMore = useCallback(() => {
    if (hasNextPage) void fetchNextPage()
  }, [fetchNextPage, hasNextPage])
  useEffect(() => {
    const observer = new IntersectionObserver(() => loadMore())
    return () => observer.disconnect()
  }, [loadMore])
  return <div />
}
"""

WITH_BUTTON = SCROLL_ONLY.replace("return <div />", "return <Button onClick={loadMore}>Show older</Button>").replace(
    "void fetchNextPage()", "void fetchNextPage({ cancelRefetch: false })"
)
TWICE = WITH_BUTTON.replace("void fetchNextPage({ cancelRefetch: false })", "void fetchNextPage()")


def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_unpaged_lists", REPOSITORY_ROOT / "scripts" / "check_unpaged_lists.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_unpaged_lists"] = module
    spec.loader.exec_module(module)
    return module


def test_a_list_drawn_in_full_in_a_wrapping_row_is_found(tmp_path: Path) -> None:
    check = script()
    view = tmp_path / "Writers.tsx"
    view.write_text(UNPAGED, encoding="utf-8")
    assert [item.source for item in check.unpaged_in(view)] == ["link.writers"]


def test_a_paged_list_and_a_fixed_list_pass(tmp_path: Path) -> None:
    check = script()
    for name, text in (("Paged.tsx", PAGED), ("Fixed.tsx", FIXED)):
        view = tmp_path / name
        view.write_text(text, encoding="utf-8")
        assert check.unpaged_in(view) == []


def test_the_app_draws_no_open_list_in_full() -> None:
    check = script()
    assert [item for path in check.sources() for item in check.unpaged_in(path)] == []


def test_a_feed_that_loads_only_on_scroll_is_found_and_one_with_a_button_passes(tmp_path: Path) -> None:
    check = script()
    scroll = tmp_path / "Feed.tsx"
    scroll.write_text(SCROLL_ONLY, encoding="utf-8")
    assert [item.source for item in check.unpaged_in(scroll)] == ["fetchNextPage"]
    button = tmp_path / "Button.tsx"
    button.write_text(WITH_BUTTON, encoding="utf-8")
    assert check.unpaged_in(button) == []


def test_a_feed_loaded_by_scroll_and_button_must_not_ask_for_a_page_twice(tmp_path: Path) -> None:
    check = script()
    twice = tmp_path / "Twice.tsx"
    twice.write_text(TWICE, encoding="utf-8")
    assert [item.source for item in check.unpaged_in(twice)] == ["fetchNextPage twice"]
