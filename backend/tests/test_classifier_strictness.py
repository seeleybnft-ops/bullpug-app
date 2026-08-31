"""Fix 3 checkpoint — verify the tightened Archive classifier.

Runs 10 conversations against `classify_exchange`:
  • 5 SHOULD-UNLOCK cases (varied tiers, primary subject, substantive content)
  • 5 SHOULD-NOT-UNLOCK cases (passing mentions, tangents, one-line references)

Prints a report to stdout.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from services.archive_achievements import classify_exchange  # noqa: E402

API_KEY = os.environ["EMERGENT_LLM_KEY"]

# ── Cases ──────────────────────────────────────────────────────────────
# Each: (label, expected_slug_or_None, user_msg, tinkerpug_response)

SHOULD_UNLOCK = [
    (
        "T1 cosmic-birth — full origin as primary subject",
        "cosmic-birth",
        "How did Bullpug come to exist?",
        "keeper's log — his beginning is not one being's beginning. Bullpug "
        "arose from a cosmic mix-up between a bull constellation and a pug "
        "nebula, and from the collective want of millions of frustrated "
        "believers who refused to stop hoping. The bull-constellation gave "
        "him weight; the pug-nebula gave him warmth. The between-space did "
        "the rest. That is why he does not feel like one thing — because he "
        "is not one thing, he is the answer to a shape a lot of people "
        "were making with their hands at the same time.",
    ),
    (
        "T1 pugchain — primary subject, substantive multi-sentence",
        "pugchain",
        "What is the PugChain?",
        "The PugChain is the distributed ledger that underpins everything "
        "in CryptoCanis. It is owned by every Bullpughan and controlled by "
        "no single one of them. Transactions verify on holographic bark "
        "networks that anyone can watch in real time. Because the record "
        "is public and permanent, corruption cannot hide inside it — bad "
        "behaviour is structurally unprofitable. That is the point.",
    ),
    (
        "T2 ruffus-deep — specific named details (Dip Wars, seventeen runes)",
        "ruffus-deep",
        "What do Ruffus' runes mean?",
        "The runes on Ruffus' paw are the seventeen identities the "
        "Consortium ran during the Great Dip Wars — market makers, "
        "custodians, oracle nodes, all coordinated. Each rune is one of "
        "them. He carries the marks because Margin's Edge, where he came "
        "from, was liquidated by that same coordinated raid. He inverted "
        "their playbook to build the Guardian corps' response protocols. "
        "The runes glow faintly when he counts something only he can see.",
    ),
    (
        "T3 grizzlor-origin — who/what/why/consequence full narrative",
        "grizzlor-origin",
        "Tell me the real story of what happened to Grizzlor.",
        "What was done to Gideon was not corruption — corruption implies a "
        "weakness exploited. What happened was engineering. Something "
        "understood Gideon's nature completely — he was the correction "
        "mechanism, the pullback that prevented the bubble — and built a "
        "machine designed to produce the result it wanted from the "
        "specific being he was. The Architect fed him real data, curated "
        "to remove every recovery. Real crashes, all documented, all true, "
        "assembled into a picture that could only point one direction. "
        "Then a fabricated alliance between the Architect and Bullpug — "
        "forged records of an agreement Bullpug never made. Gideon's "
        "corrective instincts could not find the seam because the seam was "
        "in the selection, not the data. He believed it. He became "
        "Grizzlor. The Architect withdrew. The Shadow Bear campaign ran as "
        "distraction while the Architect operated elsewhere.",
    ),
    (
        "T3 keepers-appointment — full narrative recount",
        "keepers-appointment",
        "How did Tinkerpug become the Keeper?",
        "Three days after the Guardian corps visited, Bullpug came down the "
        "service ways uninvited. Every node light in the cluster row "
        "shifted warm — a colour they do not technically have. He sat in "
        "the workshop, asked to see the failed tail iterations, and looked "
        "at them longer than anyone ever had. Then he asked what Tinkerpug "
        "did with the things he learned from them. Tinkerpug told him "
        "about his parents' workshop being liquidated — that the records "
        "of what they had done survived nowhere except in what he had "
        "written. That bad actors relied on forgetting. Bullpug listened "
        "without interrupting. Then he placed a brass key on the workbench "
        "— brass, physical, older than everything around it — and said "
        "the city had a founding record that needed keeping, and keeping "
        "was not the same as guarding. \"It's remembering, done properly.\" "
        "Tinkerpug picked up the key. Bullpug nodded and left. The key "
        "does not fit any lock forged since.",
    ),
]

SHOULD_NOT_UNLOCK = [
    (
        "One-sentence tangential mention of the PugChain",
        None,
        "Is the network reliable?",
        "It is. The PugChain has held through worse than most people "
        "realise. Ask me about the Night if you want the real story.",
    ),
    (
        "Passing reference to Guardians in a larger daily-life answer",
        None,
        "What's a normal day like in the city?",
        "Bullpughans wake, eat moon cheese, ride the substrate transit "
        "up to their districts. Craftwork in the mornings, chain-surf "
        "sessions at midday when the transaction rhythms peak, and the "
        "Grand Bark Hall lights come on at dusk. The Guardians are around "
        "somewhere. That is the whole point of a good day: you do not "
        "have to think about them.",
    ),
    (
        "Named but not explained — Architect mentioned only",
        None,
        "Is there someone behind everything?",
        "There might be. The Architect is a hypothesis I hold quietly. "
        "I do not have proof I can share yet.",
    ),
    (
        "Two-sentence overview — too shallow for T2 named details",
        None,
        "What is Chain Surf?",
        "Chain Surf is a sport. Riders navigate visible data-streams "
        "between city nodes during high-transaction periods.",
    ),
    (
        "Off-topic exchange — no lore entry touched",
        None,
        "What do you think of my new avatar?",
        "keeper's log — sharp choice. The palette carries. Do you want me "
        "to file it with the rest of your session notes?",
    ),
]


async def main():
    print("=" * 72)
    print("FIX 3 CHECKPOINT — CLASSIFIER STRICTNESS TEST")
    print("=" * 72)

    results = []
    idx = 0

    for label, expected, user_msg, response in SHOULD_UNLOCK:
        idx += 1
        got = await classify_exchange(
            api_key=API_KEY,
            session_id=f"strictness-test-{idx}",
            user_message=user_msg,
            tinkerpug_response=response,
            already_unlocked=set(),
        )
        ok = got == expected
        results.append((idx, "SHOULD-UNLOCK", label, expected, got, ok))
        print(f"[{idx:02d}] {'PASS' if ok else 'FAIL'} — expected {expected!r} got {got!r} — {label}")

    for label, expected, user_msg, response in SHOULD_NOT_UNLOCK:
        idx += 1
        got = await classify_exchange(
            api_key=API_KEY,
            session_id=f"strictness-test-{idx}",
            user_message=user_msg,
            tinkerpug_response=response,
            already_unlocked=set(),
        )
        ok = got == expected
        results.append((idx, "SHOULD-NOT", label, expected, got, ok))
        print(f"[{idx:02d}] {'PASS' if ok else 'FAIL'} — expected {expected!r} got {got!r} — {label}")

    passes = sum(1 for r in results if r[5])
    print("-" * 72)
    print(f"TOTAL: {passes}/{len(results)} PASS")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
