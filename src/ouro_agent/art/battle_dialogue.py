"""Situational battle dialogue for heroes.

Dialogue is presentation-only: it reacts to battle facts but never changes
combat rules.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ouro_agent.tui.frame_builder import BattleFrame


DIALOGUE_CATEGORIES = (
    "intro",
    "advantage",
    "low_hp",
    "mp_low",
    "interrupt_success",
    "build_trigger",
    "boss_phase",
    "near_defeat",
)


HERO_DIALOGUE: dict[str, dict[str, dict[str, list[str]]]] = {
    "hero_shadow_apprentice": {
        "intro": {
            "en": [
                "The candle wakes. Keep your eyes on the dark.",
                "I will spend shadow only where it buys time.",
                "One flame, one field, one mistake less.",
            ],
            "zh": [
                "烛火醒了。盯紧黑暗。",
                "我只在能换来节奏的地方花掉暗影。",
                "一束火，一片战场，少犯一个错。",
            ],
        },
        "advantage": {
            "en": [
                "The dark has found its mark.",
                "Their chant is thinner now.",
                "Hold the line. The seal is working.",
            ],
            "zh": [
                "黑暗已经找到了落点。",
                "他们的咏唱变薄了。",
                "稳住。封印正在生效。",
            ],
        },
        "low_hp": {
            "en": [
                "The candle is guttering. One seal left, if I can pay for it.",
                "Too little blood left for careless magic.",
                "The flame bends, but it has not gone out.",
            ],
            "zh": [
                "烛火快灭了。若我还付得起代价，就再封一次。",
                "血太少了，不能再随便施法。",
                "火焰弯下去了，但还没灭。",
            ],
        },
        "mp_low": {
            "en": [
                "I cannot seal the next chant without more echo.",
                "The wick is dry. No waste now.",
                "If another caster rises, I may not have the price.",
            ],
            "zh": [
                "没有更多回响，我封不住下一次咏唱。",
                "烛芯干了。现在不能浪费。",
                "若又有施法者起势，我未必付得起代价。",
            ],
        },
        "interrupt_success": {
            "en": [
                "There. The wick forgets its prayer.",
                "The chant breaks before it becomes a wound.",
                "Silence is cheaper than blood.",
            ],
            "zh": [
                "就是那里。烛芯忘记了它的祷词。",
                "咏唱在变成伤口之前断掉了。",
                "沉默比流血便宜。",
            ],
        },
        "build_trigger": {
            "en": [
                "The black candle answers as a pattern, not a spark.",
                "Shadow and control have found each other.",
                "This is no longer a trick. It is a method.",
            ],
            "zh": [
                "黑烛回应的不再是火花，而是阵式。",
                "暗影和控制终于咬合了。",
                "这不再是把戏，是方法。",
            ],
        },
        "boss_phase": {
            "en": [
                "That flame has a second wick. Watch the turn.",
                "The rite changes shape. Keep a seal ready.",
                "This is where the Codex stops whispering and starts warning.",
            ],
            "zh": [
                "那团火还有第二根烛芯。看准转折。",
                "仪式变形了。留一个封印。",
                "秘典不再低语，它开始警告。",
            ],
        },
        "near_defeat": {
            "en": [
                "Last candle. Last breath. Still enough.",
                "If this is the final seal, make it count.",
                "The dark is close enough to touch. So is victory.",
            ],
            "zh": [
                "最后一支烛，最后一口气。仍然够用。",
                "若这是最后一道封印，就让它值得。",
                "黑暗近得能摸到。胜利也是。",
            ],
        },
    },
    "hero_ash_guardian": {
        "intro": {
            "en": [
                "Stand behind the shield. Count the openings.",
                "The tower does not rush. It waits, then moves.",
                "Let them spend their anger on iron.",
            ],
            "zh": [
                "站到盾后。数清破绽。",
                "高塔不急。它等待，然后推进。",
                "让他们把怒火花在铁上。",
            ],
        },
        "advantage": {
            "en": [
                "Now the wall moves forward.",
                "They are tired. Good. The shield is not.",
                "One more step, and the line becomes a blade.",
            ],
            "zh": [
                "现在，城墙开始前进。",
                "他们累了。很好，盾还没有。",
                "再进一步，防线就会变成刀锋。",
            ],
        },
        "low_hp": {
            "en": [
                "The shield is splitting, but the line still holds.",
                "Armor can crack. Oaths do not.",
                "I need one clean brace before the next blow.",
            ],
            "zh": [
                "盾面裂开了，但防线还在。",
                "甲会裂，誓言不会。",
                "下一击前，我需要一次稳固防御。",
            ],
        },
        "mp_low": {
            "en": [
                "No ash left for tricks. Only iron.",
                "The ember is low. I will have to make the block matter.",
                "No more glare. Let the shield speak.",
            ],
            "zh": [
                "没有余烬能变招了，只剩铁。",
                "余烬不足了。每次格挡都必须有意义。",
                "没有余力瞪视了，让盾说话。",
            ],
        },
        "interrupt_success": {
            "en": [
                "Your ritual breaks against the tower.",
                "I heard the chant hit the shield and die.",
                "A wall can interrupt, if it is patient.",
            ],
            "zh": [
                "你的仪式撞碎在塔盾上。",
                "我听见咏唱撞上盾，然后死掉。",
                "墙足够耐心，也能打断。",
            ],
        },
        "build_trigger": {
            "en": [
                "Guard becomes iron. Iron becomes answer.",
                "The legion stands in one shield.",
                "Now every block has a memory.",
            ],
            "zh": [
                "守势成铁，铁成答案。",
                "军团立在一面盾里。",
                "现在，每次格挡都有记忆。",
            ],
        },
        "boss_phase": {
            "en": [
                "Bigger rite. Same shield. Watch the charge.",
                "That phase wants patience, not panic.",
                "When it overreaches, the tower answers.",
            ],
            "zh": [
                "更大的仪式，同一面盾。看蓄力。",
                "这个阶段要耐心，不要慌。",
                "它伸得太远时，高塔会回应。",
            ],
        },
        "near_defeat": {
            "en": [
                "If I fall, I fall facing it.",
                "The last block is still a block.",
                "Break me later. Stop me now, if you can.",
            ],
            "zh": [
                "若我倒下，也会面朝它倒下。",
                "最后一次格挡，仍然是格挡。",
                "要打碎我可以稍后。现在先试着拦住我。",
            ],
        },
    },
    "hero_broken_string_hunter": {
        "intro": {
            "en": ["String drawn. Pick the weak point.", "I only need one clean line.", "Fast fight, quiet exit."],
            "zh": ["弦已拉开。找弱点。", "我只需要一条干净的线。", "快战，安静离场。"],
        },
        "advantage": {
            "en": ["They're bleeding. Now we count down.", "The shot is lining itself up.", "Pressure makes targets honest."],
            "zh": ["他们在流血。现在开始倒数。", "准星自己排好了。", "压力会让目标变诚实。"],
        },
        "low_hp": {
            "en": ["Blood in my eye. Aim still clear.", "Too close. I shoot better close.", "Pain is noise. The target is signal."],
            "zh": ["血进了眼睛，准星还在。", "太近了。我近处更准。", "痛是噪音，目标是信号。"],
        },
        "mp_low": {
            "en": ["No room for flourishes. One clean shot.", "Tricks are gone. Bolts remain.", "Save the last step for the kill."],
            "zh": ["没余地炫技了，只剩一发准的。", "花招没了，弩矢还在。", "把最后一步留给击杀。"],
        },
        "interrupt_success": {
            "en": ["Cut the string. Drop the song.", "Their rhythm is mine now.", "A hook in the chant, and it tears."],
            "zh": ["割断弦，歌就落地。", "他们的节奏现在归我了。", "咏唱被钩住，就会撕开。"],
        },
        "build_trigger": {
            "en": ["Bleed becomes a map.", "The hunt rite is awake.", "Every wound points to the last one."],
            "zh": ["流血变成了地图。", "狩猎仪式醒了。", "每道伤口都指向最后一下。"],
        },
        "boss_phase": {
            "en": ["New phase. Same throat.", "Big targets still have strings.", "Wait for the overreach."],
            "zh": ["新阶段，同一个喉咙。", "大目标也有弦。", "等它伸得太远。"],
        },
        "near_defeat": {
            "en": ["Too close. Good. I shoot better there.", "Last bolt. Make it ugly.", "If I miss, I die. So I won't."],
            "zh": ["太近了。很好，我近处更准。", "最后一矢。让它难看点。", "我若失手就会死。所以不会。"],
        },
    },
    "hero_mire_oracle": {
        "intro": {
            "en": ["The mire is patient. So am I.", "Let the first drop teach them fear.", "Omen first, poison after."],
            "zh": ["瘴沼很有耐心。我也是。", "让第一滴毒教会他们恐惧。", "先下厄兆，再下毒。"],
        },
        "advantage": {
            "en": ["Now the sickness starts counting.", "They are already losing. Slowly.", "Do not rush poison. It hates that."],
            "zh": ["现在，病开始计数。", "他们已经在输了。只是慢一点。", "别催毒。毒不喜欢被催。"],
        },
        "low_hp": {
            "en": ["The veil tears. The vial does not.", "Too much blood in the water.", "I need the mire to buy one more breath."],
            "zh": ["面纱破了，毒瓶还没破。", "水里的血太多了。", "我需要瘴沼再买一口气。"],
        },
        "mp_low": {
            "en": ["The vial is nearly dry.", "No more omens to spare.", "One poison left. Spend it like a verdict."],
            "zh": ["毒瓶快干了。", "没有多余厄兆了。", "只剩一份毒，把它当判决花掉。"],
        },
        "interrupt_success": {
            "en": ["Their breath catches in the fog.", "The chant sinks before it rises.", "Mire in the throat. Silence follows."],
            "zh": ["他们的呼吸卡在雾里。", "咏唱还没升起就沉下去了。", "瘴沼入喉，沉默随后。"],
        },
        "build_trigger": {
            "en": ["Poison has found its circle.", "The omen and vial agree.", "Attrition is a promise kept slowly."],
            "zh": ["毒找到了它的环。", "厄兆和毒瓶达成一致。", "消耗是一种慢慢兑现的承诺。"],
        },
        "boss_phase": {
            "en": ["Large bodies rot by stages.", "The phase changes. The fever remains.", "Mark the pulse, then spoil it."],
            "zh": ["巨大的身体会分阶段腐坏。", "阶段变了，热病还在。", "标记脉搏，然后毁掉它。"],
        },
        "near_defeat": {
            "en": ["If I drown, the mire comes with me.", "Last breath. Bitter enough.", "The swamp takes slowly. Even me."],
            "zh": ["若我沉没，瘴沼会一起下去。", "最后一口气，够苦。", "沼泽吞得很慢，包括我。"],
        },
    },
    "hero_gravewright": {
        "intro": {
            "en": ["Gear set. Nail ready.", "Let the grave engine warm up.", "Measure twice. Bury once."],
            "zh": ["齿轮就位，坟钉备好。", "让坟场机关热起来。", "量两次，埋一次。"],
        },
        "advantage": {
            "en": ["The machine likes this angle.", "Now the nail remembers its work.", "The trap is no longer theoretical."],
            "zh": ["机器喜欢这个角度。", "现在，钉子想起了它的工作。", "陷阱不再只是理论。"],
        },
        "low_hp": {
            "en": ["Gears skip. Hands steady.", "The crate is smoking. Keep turning.", "If it breaks, I build with the pieces."],
            "zh": ["齿轮跳齿，手不能抖。", "箱子冒烟了。继续转。", "若它坏掉，我就用碎片再造。"],
        },
        "mp_low": {
            "en": ["No charge left. Use the nail.", "The engine coughs. Manual work, then.", "Save the crank for the real opening."],
            "zh": ["没有充能了，用钉子。", "机关在咳嗽。那就手动干活。", "把曲柄留给真正的窗口。"],
        },
        "interrupt_success": {
            "en": ["A nail in the ritual joint.", "That chant had bad engineering.", "Break the hinge, stop the door."],
            "zh": ["一根钉子钉进仪式关节。", "那段咏唱的工程学太差。", "断铰链，门就停。"],
        },
        "build_trigger": {
            "en": ["The grave engine is online.", "Trap, gear, nail. A proper sentence.", "Now the machine speaks in impacts."],
            "zh": ["坟场机关上线了。", "陷阱、齿轮、钉子。一句完整的话。", "现在机器用冲击说话。"],
        },
        "boss_phase": {
            "en": ["Big mechanism. Bigger failure point.", "Phase change means new hinge.", "Find the joint before it finds us."],
            "zh": ["大机制，更大的故障点。", "阶段变化意味着新铰链。", "先找到关节，别让它先找到我们。"],
        },
        "near_defeat": {
            "en": ["Last nail. Deepest one.", "If I fall, the trap still bites.", "One more turn of the crank."],
            "zh": ["最后一钉，钉得最深。", "若我倒下，陷阱仍会咬人。", "曲柄再转一圈。"],
        },
    },
    "hero_echo_exile": {
        "intro": {
            "en": ["The bell is cracked. It still answers.", "Listen first. Strike second.", "Every echo has a cost."],
            "zh": ["铃裂了，但还会回应。", "先听，再出手。", "每个回声都有代价。"],
        },
        "advantage": {
            "en": ["The room is singing back.", "Their noise is becoming my hymn.", "Echoes stack. So do chances."],
            "zh": ["房间正在回唱。", "他们的噪音正在变成我的圣歌。", "回声会叠，机会也是。"],
        },
        "low_hp": {
            "en": ["The hymn is thin. Still tuned.", "Too much silence in my chest.", "One clean bell before the dark."],
            "zh": ["圣歌变薄了，音还准。", "胸口里的沉默太多了。", "黑暗前，再敲一次准的。"],
        },
        "mp_low": {
            "en": ["No echo left to waste.", "The next note must carry itself.", "I cannot cleanse what I cannot pay for."],
            "zh": ["没有回声能浪费了。", "下一音必须自己站住。", "付不起代价，就净化不了。"],
        },
        "interrupt_success": {
            "en": ["I took the note out of their mouth.", "Their chant returns as silence.", "A broken bell can still stop a prayer."],
            "zh": ["我把音从他们嘴里取走了。", "他们的咏唱作为沉默返回。", "破铃仍能截住祈祷。"],
        },
        "build_trigger": {
            "en": ["The echo wall is listening.", "Cleanse and return. The circuit closes.", "Now the bell remembers for me."],
            "zh": ["回声护壁正在聆听。", "净化，然后返回。回路闭合。", "现在，铃替我记住了。"],
        },
        "boss_phase": {
            "en": ["That phase rings wrong. Good. I can hear it.", "The larger the rite, the louder the flaw.", "Let it sing once. Then answer."],
            "zh": ["那个阶段音不准。很好，我听得见。", "仪式越大，破绽越响。", "让它唱一次，然后回应。"],
        },
        "near_defeat": {
            "en": ["Last echo. Let it return sharp.", "If I go quiet, make the silence useful.", "One broken bell. One final note."],
            "zh": ["最后一道回声，让它锋利地回来。", "若我沉默，就让沉默有用。", "一只破铃，最后一音。"],
        },
    },
}


def select_dialogue_line(
    hero_id: str,
    *,
    frame: BattleFrame | None,
    hp_pct: float,
    mp_pct: float,
    lang: str,
    tick: int = 0,
) -> str | None:
    category = _select_category(frame=frame, hp_pct=hp_pct, mp_pct=mp_pct)
    table = HERO_DIALOGUE.get(hero_id)
    if table is None:
        return None
    localized = table.get(category, {}).get(lang) or table.get(category, {}).get("en")
    if not localized:
        localized = table.get("intro", {}).get(lang) or table.get("intro", {}).get("en")
    if not localized:
        return None
    return localized[tick % len(localized)]


def _select_category(*, frame: BattleFrame | None, hp_pct: float, mp_pct: float) -> str:
    if hp_pct < 0.18:
        return "near_defeat"
    if hp_pct < 0.3:
        return "low_hp"
    if frame is not None:
        if frame.event_banner in {"BUILD ONLINE", "HIGH ROLL"}:
            return "build_trigger"
        if frame.event_banner and "PHASE" in frame.event_banner:
            return "boss_phase"
        if frame.event_banner in {"CHARGE BROKEN", "SEAL PLACED", "BREAK WINDOW OPEN"}:
            return "interrupt_success"
        if "CLIMAX" in (frame.event_banner or ""):
            return "advantage"
        if "MP below" in frame.risk or "last 18 MP" in frame.risk:
            return "mp_low"
    if mp_pct < 0.25:
        return "mp_low"
    return "intro"
