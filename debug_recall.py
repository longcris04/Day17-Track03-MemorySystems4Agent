#!/usr/bin/env python3
"""Debug why recall is 0."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent_advanced import AdvancedAgent
from config import load_config
from memory_store import extract_profile_updates
import tempfile

def test_profile_extraction():
    """Test if profile extraction works."""
    print("=" * 60)
    print("TEST 1: Profile Extraction")
    print("=" * 60)

    message = "Chào bạn, mình tên là DũngCT."
    facts = extract_profile_updates(message)
    print(f"Message: '{message}'")
    print(f"Extracted facts: {facts}")
    print()

    if not facts:
        print("❌ No facts extracted!")
    else:
        print(f"✓ Extracted {len(facts)} fact(s)")
    print()


def test_user_md_update():
    """Test if User.md gets updated."""
    print("=" * 60)
    print("TEST 2: User.md Update")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp_dir:
        from config import LabConfig
        from model_provider import ProviderConfig

        config = LabConfig(
            base_dir=Path(tmp_dir),
            data_dir=Path(tmp_dir) / "data",
            state_dir=Path(tmp_dir) / "state",
            compact_threshold_tokens=4000,
            compact_keep_messages=10,
            model=ProviderConfig(
                provider='openrouter',
                model_name='google/gemini-2.5-flash-lite',
                temperature=0.3,
                api_key='dummy'
            ),
            judge_model=ProviderConfig(
                provider='openrouter',
                model_name='google/gemini-2.5-flash-lite',
                temperature=0.0,
                api_key='dummy'
            ),
        )

        agent = AdvancedAgent(config, force_offline=True)
        user_id = 'testuser'

        print(f"Initial User.md:")
        initial = agent.profile_store.read_text(user_id)
        print(initial[:200] + "...")
        print()

        # Send a message with name
        print(f"Sending message: 'Chào bạn, mình tên là DũngCT'")
        result = agent.reply(user_id, 'thread1', 'Chào bạn, mình tên là DũngCT')
        print(f"Response: {result['response']}")
        print()

        print(f"Updated User.md:")
        updated = agent.profile_store.read_text(user_id)
        print(updated)
        print()

        if 'DũngCT' in updated:
            print("✓ Name was updated in User.md")
        else:
            print("❌ Name NOT in User.md")
        print()


def test_recall_question():
    """Test if recall questions get answered correctly."""
    print("=" * 60)
    print("TEST 3: Recall Question")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp_dir:
        from config import LabConfig
        from model_provider import ProviderConfig

        config = LabConfig(
            base_dir=Path(tmp_dir),
            data_dir=Path(tmp_dir) / "data",
            state_dir=Path(tmp_dir) / "state",
            compact_threshold_tokens=4000,
            compact_keep_messages=10,
            model=ProviderConfig(
                provider='openrouter',
                model_name='google/gemini-2.5-flash-lite',
                temperature=0.3,
                api_key='dummy'
            ),
            judge_model=ProviderConfig(
                provider='openrouter',
                model_name='google/gemini-2.5-flash-lite',
                temperature=0.0,
                api_key='dummy'
            ),
        )

        agent = AdvancedAgent(config, force_offline=True)
        user_id = 'testuser'

        # Session 1: Tell name
        print("Session 1: Telling name")
        result1 = agent.reply(user_id, 'session1', 'Mình tên là Alice')
        print(f"Response: {result1['response']}")
        print()

        # Session 2: Ask name (fresh thread)
        print("Session 2: Asking name (fresh thread)")
        result2 = agent.reply(user_id, 'session2', 'Mình tên gì?')
        answer = result2['response']
        print(f"Response: {answer}")
        print()

        # Check if answer contains expected fact
        expected = ['Alice']
        from benchmark import recall_points
        recall = recall_points(answer, expected)
        print(f"Expected to find: {expected}")
        print(f"Recall score: {recall}")
        print()

        if 'Alice' in answer:
            print("✓ Answer contains expected fact")
        else:
            print("❌ Answer does NOT contain expected fact")
            print(f"\nUser.md content:")
            print(agent.profile_store.read_text(user_id))
        print()


def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + "  Debugging Recall = 0 Issue".center(58) + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    test_profile_extraction()
    test_user_md_update()
    test_recall_question()

    print("=" * 60)
    print("Debug complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
