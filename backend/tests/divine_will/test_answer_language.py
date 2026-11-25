from aerona.prompts.schemas.divine_will import WillAnswerInLanguage
from tests.api.conftest import ApiWorld
from tests.divine_will.conftest import ask
from tests.divine_will.scripted import Say, ScriptedWill

TURKISH = "D\u00fcnyan\u0131n en kalabal\u0131k yerle\u015fiminin refah\u0131n\u0131 on puan art\u0131r, l\u00fctfen."
ENGLISH_ANSWER = "The prosperity of the largest settlement rose by ten points, from seventy five to eighty five."
TURKISH_ANSWER = "En b\u00fcy\u00fck yerle\u015fimin refah\u0131 on puan artt\u0131, yetmi\u015f be\u015ften seksen be\u015fe \u00e7\u0131kt\u0131."


async def test_an_answer_in_another_language_is_written_again_in_the_players(will: ApiWorld, will_model: ScriptedWill) -> None:
    will_model.plan([Say(ENGLISH_ANSWER)])
    will_model.script(WillAnswerInLanguage, WillAnswerInLanguage(text=TURKISH_ANSWER))
    cycle = await ask(will, TURKISH)
    assert cycle["status"] == "done", cycle
    assert cycle["final_text"] == TURKISH_ANSWER
    notices = [event["payload"] for event in cycle["events"] if event["kind"] == "notice"]
    assert any(notice.get("notice") == "translated" and notice.get("language") == "Turkish" for notice in notices)
    asked = [call for call in will_model.calls if call.label == "divine_will_language"]
    assert len(asked) == 1 and "Turkish" in asked[0].prompt and ENGLISH_ANSWER in asked[0].prompt


async def test_an_answer_already_in_the_players_language_is_kept(will: ApiWorld, will_model: ScriptedWill) -> None:
    will_model.plan([Say(TURKISH_ANSWER)])
    cycle = await ask(will, TURKISH)
    assert cycle["final_text"] == TURKISH_ANSWER
    assert not [call for call in will_model.calls if call.label == "divine_will_language"]
