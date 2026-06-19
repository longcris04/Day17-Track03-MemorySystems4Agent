import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import load_config
from pathlib import Path
from agent_advanced import AdvancedAgent
from memory_store import extract_profile_updates

config = load_config(Path(__file__).resolve().parent)
agent = AdvancedAgent(config, force_offline=False)
print('langchain_agent:', type(agent.langchain_agent).__name__)

user_id = 'dungct'
turns = [
    'Chao ban, minh ten la DungCT.',
    'Minh o Da Nang va dang lam backend engineer cho startup AI.',
    'Minh thich Python, AI ung dung va ca phe sua da.',
    'Chào bạn, mình tên là DũngCT.',
    'Mình ở Đà Nẵng và đang làm backend engineer cho startup AI.',
]
for i, msg in enumerate(turns):
    updates = extract_profile_updates(msg)
    print(f'\nTurn {i+1}: updates={updates}')
    result = agent.reply(user_id, 'conv-01', msg)
    print(f'  response: {result["response"][:80]}')

profile_path = agent.profile_store.path_for(user_id)
print(f'\nProfile path: {profile_path}')
print(f'Profile exists: {profile_path.exists()}')
if profile_path.exists():
    print(profile_path.read_text(encoding='utf-8')[:400])
else:
    print('Profile NOT written!')
