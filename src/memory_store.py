from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Ước tính số token từ text (không cần accuracy cao).

    Flow: Agent dùng hàm này để:
    - Kiểm tra xem thread đã vượt ngưỡng compact chưa
    - Tính token usage cho benchmarking
    - Quyết định khi nào nên compact memory

    Chiến lược: Các LLM thường mã hóa ~1 token per 4 ký tự (rough estimate).
    """
    if not text or not text.strip():
        return 0
    # Loại bỏ leading/trailing whitespace, ước tính tokens
    return len(text.strip()) // 4 + 1


@dataclass
class UserProfileStore:
    """Lưu trữ bền vững User.md cho mỗi user.

    Flow:
    1. Agent gọi read_text(user_id) để lấy profile hiện tại
    2. Agent extract profile updates từ user message
    3. Agent gọi write_text hoặc edit_text để cập nhật
    4. Benchmark gọi file_size để đo memory growth

    Mỗi user có một file User.md riêng, ví dụ:
    - state/profiles/dungct.md
    - state/profiles/dungct_stress.md
    """

    root_dir: Path

    def path_for(self, user_id: str) -> Path:
        """Tạo path an toàn cho user ID.

        Slugify: loại bỏ ký tự đặc biệt, thay spaces bằng underscore.
        Mục đích: tránh path traversal hoặc ký tự không hợp lệ.
        """
        # Sanitize: chỉ giữ alphanumeric, underscore, hyphen
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', user_id)
        if not safe_id:
            safe_id = 'default'
        return self.root_dir / f'{safe_id}.md'

    def read_text(self, user_id: str) -> str:
        """Đọc User.md hiện tại hoặc trả về template mặc định.

        Mục đích: Agent có User.md để reference khi trả lời,
        ngay cả lần đầu tiên làm quen user.
        """
        path = self.path_for(user_id)
        if path.exists():
            return path.read_text(encoding='utf-8')
        # Default template cho user mới
        return f"""# User Profile: {user_id}

## Personal Information
- Name: (unknown)
- Location: (unknown)
- Profession: (unknown)

## Preferences
- Response style: (learning)
- Favorite food: (unknown)
- Favorite drink: (unknown)

## Hobbies & Interests
- (unknown)

---
*Auto-generated profile. Updated as we learn more about you.*
"""

    def write_text(self, user_id: str, content: str) -> Path:
        """Ghi (overwrite) toàn bộ User.md.

        Mục đích: Advanced agent ghi profile update sau mỗi lượt.
        """
        path = self.path_for(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        """Replace một occurrence của search_text bằng replacement.

        Mục đích: Update cụ thể một field (vd: tên, địa chỉ) mà không touch phần khác.
        Trả về True nếu thay đổi được, False nếu search_text không tìm thấy.
        """
        path = self.path_for(user_id)
        if not path.exists():
            return False

        content = path.read_text(encoding='utf-8')
        if search_text not in content:
            return False

        # Replace chỉ lần đầu tiên (count=1) để tránh side effects
        new_content = content.replace(search_text, replacement, 1)
        path.write_text(new_content, encoding='utf-8')
        return True

    def file_size(self, user_id: str) -> int:
        """Kích thước file User.md hiện tại (bytes).

        Mục đích: Benchmark đo lường memory growth (profile phải duy trì nhỏ gọn).
        """
        path = self.path_for(user_id)
        if not path.exists():
            return 0
        return path.stat().st_size


def extract_profile_updates(message: str) -> dict[str, str]:
    """Trích xuất profile facts từ user message.

    Flow: Agent gọi hàm này sau mỗi user message để:
    - Tìm tên ("Tôi tên là X", "Mình là Y")
    - Tìm địa chỉ ("Tôi ở TP.HCM", "Mình từ Đà Nẵng")
    - Tìm nghề ("Tôi là backend engineer", "Làm tester")
    - Tìm sở thích ("Tôi thích cà phê", "Yêu chạy bộ")
    - Tìm style trả lời ("Trả lời ngắn gọn", "3 bullet points")

    Mục đích: Chỉ extract facts mạnh, skip question-only turns.
    Kết quả: Dict với keys như 'name', 'location', 'profession', ...
    """
    updates = {}

    # Pattern 1: Tên (Tôi tên là X / Mình là Y)
    name_match = re.search(
        r'(?:tôi|mình)(?:\s+tên\s+là|[\s:]+là|[\s:]+)\s*([A-Z][a-zA-Zàáãạảăằắẳẵặâầấẩẫậèéẽẹẻêềếểễệìíĩịỉòóõọỏôồốổỗộơờớởỡợùúũụủưừứửữựỳýỵỷỹđ\s\-]+)',
        message,
        re.IGNORECASE
    )
    if name_match:
        name = name_match.group(1).strip().title()
        if len(name) > 2:  # Filter noise
            updates['name'] = name

    # Pattern 2: Địa chỉ (ở / từ [place])
    location_match = re.search(
        r'(?:ở|từ|sống ở|đến từ)\s+([A-Z][a-zA-Zàáãạảăằắẳẵặâầấẩẫậèéẽẹẻêềếểễệìíĩịỉòóõọỏôồốổỗộơờớởỡợùúũụủưừứửữựỳýỵỷỹđ\s\-\.]+)',
        message,
        re.IGNORECASE
    )
    if location_match:
        location = location_match.group(1).strip().title()
        updates['location'] = location

    # Pattern 3: Nghề (là / làm [job])
    profession_match = re.search(
        r'(?:là|làm)\s+([a-z\s]+(?:engineer|developer|tester|designer|analyst|manager|architect|specialist|architect|mlops|devops))',
        message,
        re.IGNORECASE
    )
    if profession_match:
        profession = profession_match.group(1).strip()
        updates['profession'] = profession

    # Pattern 4: Style trả lời (keywords: ngắn gọn, bullet, concise, brief, 3-5 points)
    if any(keyword in message.lower() for keyword in ['ngắn gọn', 'concise', 'brief', 'bullet', 'points', 'short']):
        if 'style' not in updates:
            updates['style'] = 'ngắn gọn, structure rõ ràng'

    # Pattern 5: Đồ uống yêu thích (cà phê, trà, nước, etc.)
    drink_match = re.search(
        r'(?:thích|yêu|uống)\s+([a-z\s\-]+(?:cà phê|trà|bia|nước|cacao|espresso|latte|mocha|juice))',
        message,
        re.IGNORECASE
    )
    if drink_match:
        drink = drink_match.group(1).strip()
        updates['favorite_drink'] = drink

    # Pattern 6: Sở thích / hobby (chạy bộ, bơi, đọc sách, chơi game, etc.)
    hobby_match = re.search(
        r'(?:thích|yêu|sở thích)\s+([a-z\s\-]+(?:chạy|bơi|đọc|chơi|game|du lịch|nấu ăn|chụp ảnh|photography))',
        message,
        re.IGNORECASE
    )
    if hobby_match:
        hobby = hobby_match.group(1).strip()
        updates['hobbies'] = hobby

    return updates


def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    """Tóm tắt các message cũ thành text compact.

    Flow:
    1. Khi thread vượt ngưỡng token, CompactMemoryManager gọi hàm này
    2. Lấy top max_items oldest messages (không count recent keep_messages)
    3. Tóm tắt thành 1 paragraph/section
    4. Sử dụng tóm tắt này thay vì full messages khi tính prompt context

    Hiện tại: Heuristic simple (nối messages cũ).
    Tương lai: Có thể dùng LLM để tóm tắt tốt hơn.
    """
    if not messages:
        return '[No previous context]'

    # Lấy tối đa max_items oldest messages
    old_messages = messages[:max_items]

    # Tóm tắt heuristic: list các user/assistant messages
    summary_lines = ['## Conversation Summary (Compacted)']

    for msg in old_messages:
        role = msg.get('role', 'user').upper()
        content = msg.get('content', '')[:100]  # Cắt dài để summary ngắn gọn
        summary_lines.append(f'- **{role}**: {content}...' if len(msg.get('content', '')) > 100 else f'- **{role}**: {content}')

    return '\n'.join(summary_lines)


@dataclass
class CompactMemoryManager:
    """Quản lý memory compaction cho long threads.

    Flow:
    1. Agent append message → hàm append() thêm message vào state[thread_id]
    2. append() kiểm tra: nếu total tokens > threshold → trigger compaction
    3. Compaction: tóm tắt old messages, giữ keep_messages recent messages
    4. Agent gọi context() để lấy [summary, recent messages] để pass vào prompt
    5. Benchmark đọc compaction_count() để đo hiệu quả

    Mục đích: Giữ prompt context ngắn gọn trên long threads (reduce token usage).
    """

    threshold_tokens: int  # Kích hoạt compaction khi total > threshold
    keep_messages: int  # Giữ bao nhiêu message gần nhất (full text) trong thread
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def append(self, thread_id: str, role: str, content: str) -> None:
        """Thêm message và tự động trigger compaction nếu cần.

        Các bước:
        1. Nếu thread chưa tồn tại, tạo state với messages=[], summary='', compactions=0
        2. Append message vào messages list
        3. Tính tổng tokens của toàn bộ messages
        4. Nếu > threshold: compact (tóm tắt old, keep recent, increment compactions)
        """
        if thread_id not in self.state:
            self.state[thread_id] = {
                'messages': [],
                'summary': '',
                'compactions': 0,
            }

        messages = self.state[thread_id]['messages']
        messages.append({'role': role, 'content': content})

        # Tính total tokens
        total_tokens = sum(estimate_tokens(msg['content']) for msg in messages)

        # Trigger compaction nếu vượt ngưỡng
        if total_tokens > self.threshold_tokens:
            self._compact(thread_id)

    def _compact(self, thread_id: str) -> None:
        """Thực hiện compaction: tóm tắt old messages, giữ recent messages."""
        state = self.state[thread_id]
        messages = state['messages']

        if len(messages) <= self.keep_messages:
            return  # Không cần compact nếu chưa vượt quá keep_messages

        # Lấy messages để tóm tắt (all except the last keep_messages)
        old_messages = messages[:-self.keep_messages]
        recent_messages = messages[-self.keep_messages:]

        # Tóm tắt old messages
        summary = summarize_messages(old_messages)

        # Update state: replace full messages with summary + recent
        state['messages'] = recent_messages
        state['summary'] = summary
        state['compactions'] = state.get('compactions', 0) + 1

    def context(self, thread_id: str) -> dict[str, object]:
        """Trả về context (summary + recent messages) của một thread.

        Kết quả dùng để tính prompt token load hoặc pass vào LLM prompt.
        """
        if thread_id not in self.state:
            return {'messages': [], 'summary': '', 'compactions': 0}

        return self.state[thread_id].copy()

    def compaction_count(self, thread_id: str) -> int:
        """Số lần compaction đã xảy ra trên thread này.

        Mục đích: Benchmark đo lường hiệu quả compaction.
        """
        if thread_id not in self.state:
            return 0
        return self.state[thread_id].get('compactions', 0)
