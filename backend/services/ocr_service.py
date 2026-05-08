"""
Tata - OCR & Chat Log Parser
Extracts chat messages from WeChat/WhatsApp screenshots and exports.
Supports both image OCR and direct text export parsing.
"""

import re
import base64
import json
from datetime import datetime
from typing import Optional
from io import BytesIO
from PIL import Image


class OCRService:
    """
    Multi-format chat log extractor.
    
    Supports:
    1. WeChat screenshot OCR (via multi-modal LLM)
    2. WeChat text export (.txt)
    3. WhatsApp export (.txt)
    4. JSON chat log format
    
    Pipe to LLM for OCR: sends image to vision-capable model,
    gets structured chat log back.
    """

    WECHAT_PATTERN = re.compile(
        r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\s*\d{1,2}:\d{2}(?::\d{2})?)\s+'
        r'(.+?)[:：]\s*'
        r'(.+)'
    )

    WHATSAPP_PATTERN = re.compile(
        r'\[?(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M)\]\s*'
        r'(.+?)[:：]\s*'
        r'(.+)'
    )

    @classmethod
    def parse_text_export(cls, text: str, format_type: str = "wechat") -> list[dict]:
        """Parse chat log from text export file."""
        pattern = cls.WECHAT_PATTERN if format_type == "wechat" else cls.WHATSAPP_PATTERN
        messages = []

        for match in pattern.finditer(text):
            time_str = match.group(1)
            sender = match.group(2).strip()
            content = match.group(3).strip()

            # Normalize timestamp
            try:
                if "年" in time_str:
                    ts = datetime.strptime(time_str, "%Y年%m月%d日 %H:%M:%S")
                elif "/" in time_str:
                    ts = datetime.strptime(time_str, "%m/%d/%y, %I:%M:%S %p")
                else:
                    ts = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                ts = datetime.now()

            messages.append({
                "timestamp": ts.isoformat(),
                "sender": sender,
                "content": content,
                "type": "text",
            })

        return messages

    @classmethod
    def parse_json_export(cls, data: list[dict]) -> list[dict]:
        """Parse JSON format chat log."""
        messages = []
        for item in data:
            messages.append({
                "timestamp": item.get("timestamp", datetime.now().isoformat()),
                "sender": item.get("sender", item.get("name", "")),
                "content": item.get("content", item.get("message", "")),
                "type": item.get("type", "text"),
            })
        return messages

    @classmethod
    async def ocr_screenshot(
        cls,
        image_data: bytes,
        llm_service=None,
        known_senders: list[str] = None,
    ) -> list[dict]:
        """
        OCR a WeChat chat screenshot using multi-modal LLM.
        Sends the image to a vision-capable model with a structured prompt.
        """
        if llm_service is None:
            return cls._mock_ocr_result()

        image_b64 = base64.b64encode(image_data).decode()

        senders_hint = ""
        if known_senders:
            sender_names = "\n".join([f"- {s}" for s in known_senders])
            senders_hint = f"\n已知的聊天参与者：\n{sender_names}"

        prompt = f"""请从这张微信聊天截图中提取所有聊天消息。

要求：
1. 按时间顺序提取每条消息
2. 识别每条消息的发送者
3. 提取完整的消息内容
4. 如果消息包含表情包，标注为 [表情]
5. 如果消息包含图片，标注为 [图片]
6. 如果消息包含语音，标注为 [语音]
7. 保留emoji表情符号{senders_hint}

请以JSON数组格式返回，每条消息格式：
{{"timestamp": "推测的时间", "sender": "发送者名称", "content": "消息内容", "type": "text|emoji|image|voice"}}"""

        try:
            client = llm_service.openai_client
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                        ]
                    }
                ],
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            messages = result.get("messages", result.get("data", []))
            return messages if isinstance(messages, list) else [messages]
        except Exception as e:
            print(f"OCR failed: {e}")
            return cls._mock_ocr_result()

    @classmethod
    def _mock_ocr_result(cls) -> list[dict]:
        """Fallback OCR result for demo purposes."""
        return [
            {"timestamp": datetime.now().isoformat(), "sender": "未识别", "content": "OCR未成功，请手动输入", "type": "text"}
        ]

    @classmethod
    def extract_senders(cls, messages: list[dict]) -> dict:
        """Extract unique senders and their message counts from parsed chat."""
        senders = {}
        for msg in messages:
            sender = msg.get("sender", "未知")
            if sender not in senders:
                senders[sender] = {"count": 0, "first_seen": msg.get("timestamp"), "last_seen": msg.get("timestamp")}
            senders[sender]["count"] += 1
            senders[sender]["last_seen"] = msg.get("timestamp")
        return senders

    @classmethod
    def generate_style_analysis(cls, messages: list[dict], target_sender: str) -> str:
        """Generate a style analysis prompt for LLM based on chat history."""
        target_msgs = [m for m in messages if m.get("sender") == target_sender]

        if not target_msgs:
            return "未找到该发送者的消息。"

        samples = target_msgs[-20:]  # Last 20 messages
        sample_text = "\n".join([
            f"- [{m['timestamp']}] {m['content']}"
            for m in samples
        ])

        return f"""## {target_sender} 的聊天风格分析

### 样本消息（最近20条）
{sample_text}

### 请分析以上消息中 {target_sender} 的：
1. 说话语气（温柔/活泼/高冷/幽默/毒舌…）
2. 常用词汇和口头禅
3. 标点符号使用习惯（喜欢用句号/省略号/感叹号…）
4. 表情和emoji使用频率
5. 句子长度偏好（短句/长句/混合）
6. 主动程度（经常主动找话题/被动回复居多）"""


ocr_service = OCRService()
