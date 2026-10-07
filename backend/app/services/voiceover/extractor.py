import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class ExtractionResult:
    cleaned_script: str
    original_length: int
    cleaned_length: int
    dialogue_blocks_count: int
    status: str  # "success" | "uncertain" | "no_dialogue"
    warning_message: Optional[str] = None
    extracted_blocks: List[str] = field(default_factory=list)


class VoiceoverScriptExtractor:
    """
    Dedicated extraction engine for AdGen Voice Studio.
    Extracts strictly what the voice actor / speaker actually speaks,
    ignoring 100% of production directions (scenes, visuals, camera angles,
    on-screen text, sound effects, music, marketing analyses, notes, hashtags).
    """

    # 1. Dialogue markers (VO, Voiceover, Lời thoại, Lời thoại/Voice-over, Narration, MC, Dialogue, etc.)
    # Supports markdown bullets (*, -, •), numbers (1., 2.), bold markers (**), slashes (/), brackets.
    DIALOGUE_LINE_PATTERN = re.compile(
        r'^[\s*\-•\d.]*\s*(?:\*\*)?(?:'
        r'(?:Lời\s*thoại|Kịch\s*bản\s*lời\s*thoại|Thoại|Lời\s*dẫn|Người\s*dẫn|Dẫn\s*chuyện|Giọng\s*đọc|Lời\s*đọc|MC|Host|Narrator|Narration|Dialogue|VO|Voiceover|Voice\s*[-/]?\s*over)'
        r'(?:\s*[/&|\-]\s*(?:Lời\s*thoại|Voiceover|Voice\s*[-/]?\s*over|VO|Thoại))?'
        r'|Hook\s*\d*(?:\s*\([^)]*\))?'
        r')\s*(?:\*\*)?\s*[:\-–—]\s*(.*)$',
        re.IGNORECASE
    )

    # 2. Production instruction section headers (Never spoken!)
    PRODUCTION_INSTRUCTION_HEADER_PATTERN = re.compile(
        r'^[\s*\-•\d.]*(?:#+\s*)?(?:\*\*)?(?:'
        r'Cảnh|Scene|Phân cảnh|Phân đoạn|Timeline|Thời lượng|Thời gian|'
        r'Mở đầu|Phát triển|Kết thúc|Thân bài|Cao trào|'
        r'Hình ảnh(?:\s*[/&]\s*Hành động)?|Hành động|Visual|Visuals|Visual cue|B-roll|B\s*roll|Screen\s*record|Minh họa|'
        r'Camera|Cú máy|Góc quay|Góc máy|Shot|Cận cảnh|Toàn cảnh|Trung cảnh|'
        r'Chữ trên màn hình|Chữ hiển thị|Text trên màn hình|Text hiển thị|Text on screen|On-screen text|Text Overlay|Overlay|Text|'
        r'Hiệu ứng|Hiệu ứng âm thanh|Hiệu ứng hình ảnh|SFX|Sound effect|Sound FX|Sound|'
        r'Nhạc nền|Nhạc|Music|Background music|'
        r'Chuyển cảnh|Transition|'
        r'Ý tưởng(?:\s*video)?|Mục tiêu(?:\s*quảng cáo)?|Target audience|Khách hàng mục tiêu|Bối cảnh|'
        r'Phân tích(?:\s*yêu cầu)?|Chiến lược|Strategy|'
        r'Sản phẩm hoặc dịch vụ|Đối tượng khách hàng|Vấn đề hoặc nhu cầu|Lợi ích chính|Giọng văn|'
        r'Hook đề xuất|Tiêu đề(?:\s*cho ảnh hoặc banner)?|'
        r'Caption(?:\s*tiktok)?|Hashtag|Hashtags|Mô tả|Description|'
        r'Lưu ý(?:\s*khi quay dựng|\s*sản xuất)?|Ghi chú(?:\s*đạo diễn)?|Note|Kỹ thuật|'
        r'Bảng phân cảnh|Storyboard|Title|Thumbnail|CTA(?:\s*chính|\s*đề xuất)?|Kêu gọi hành động'
        r')\s*(?:\*\*)?\s*[:\-–—]?\s*(.*)$',
        re.IGNORECASE
    )

    # Bracket cues e.g. [Hook], [Cảnh 1], [Visual], [Camera zoom], [ting]
    # Preserve spoken placeholders such as [Tên Sản Phẩm], while removing
    # bracketed production directions.
    BRACKET_CUE_PATTERN = re.compile(
        r'\[\s*(?:cảnh|scene|visual|camera|sfx|sound|nhạc|music|pause|'
        r'zoom|cut|b[\s-]*roll|ting|hiệu ứng|chuyển cảnh)\b[^\]]*\]',
        re.IGNORECASE,
    )

    # Parenthetical acting/sound cues e.g. (cười tươi), (thở dài), (pause 2s), (giọng hào hứng, phấn khích)
    PARENTHESIS_PATTERN = re.compile(r'\([^)]*\)')

    # Scene, timestamp, or header boundary pattern
    SCENE_OR_TIMESTAMP_PATTERN = re.compile(
        r'^(?:\[?\d{1,2}:\d{2}(?:\s*[-–—]\s*\d{1,2}:\d{2})?\]?|#+\s+|\*{2}(?:Mở đầu|Phát triển|Kết thúc|Thân bài|Hook|CTA|Intro|Body|Outro)[^*]*\*{2}|\[(?:Cảnh|Scene|Phân cảnh|Intro|Outro|Hook|Body|CTA|Part)[^\]]*\])',
        re.IGNORECASE
    )

    # Bullet or list item marker pattern
    BULLET_ITEM_START_PATTERN = re.compile(r'^[\s*\-•+]+\s+|\d+\.\s+')

    # Markdown formatting syntax
    MD_HEADER_PATTERN = re.compile(r'^#+\s+.*$', re.MULTILINE)
    MD_BLOCKQUOTE_PATTERN = re.compile(r'^>\s?', re.MULTILINE)
    MD_FORMATTING_PATTERN = re.compile(r'[*_~`]{1,3}')
    MD_BULLET_PREFIX_PATTERN = re.compile(r'^[\s\-*•+]+\s*')
    QUOTED_SPAN_PATTERN = re.compile(r'["“”«»]\s*([^"“”«»]+?)\s*["“”«»]')
    PURE_PARENTHETICAL_PATTERN = re.compile(r'^\([^)]*\)$')
    SCRIPT_HEADER_PATTERN = re.compile(
        r'^(?:#+\s*)?(?:kịch\s*bản|script|lời\s*thoại|voice\s*over|voiceover|'
        r'narration|phân\s*cảnh|storyboard|cảnh|scene|hook|intro|outro)\b',
        re.IGNORECASE,
    )

    @classmethod
    def _clean_spoken_text(cls, text: str) -> str:
        """
        Cleans brackets, acting notes in parentheses, outer quotation marks,
        and stray Markdown formatting from a single dialogue segment.
        """
        if not text:
            return ""

        # Remove bracket cues [Cảnh 1], [Visual], etc.
        cleaned = cls.BRACKET_CUE_PATTERN.sub('', text)

        # Remove parenthetical acting notes e.g. (Giọng điệu lôi cuốn), (cười tươi)
        cleaned = cls.PARENTHESIS_PATTERN.sub('', cleaned)

        # Remove inline dialogue prefixes if repeated
        cleaned = re.sub(
            r'^(?:(?:VO|Voiceover|Voice\s*[-/]?\s*over|Lời\s*thoại|Thoại|Lời\s*dẫn|Người\s*dẫn|Dẫn\s*chuyện|MC|Host|Narrator|Narration|Dialogue)(?:\s*[/&|\-]\s*(?:Lời\s*thoại|Voiceover|Voice\s*[-/]?\s*over|VO|Thoại))?)\s*:\s*',
            '',
            cleaned,
            flags=re.IGNORECASE
        )

        # Remove Markdown formatting characters (*, _, `, ~)
        cleaned = cls.MD_FORMATTING_PATTERN.sub('', cleaned)

        # Remove quotes wrapping dialogue e.g. "Xin chào các bạn!" -> Xin chào các bạn!
        cleaned = re.sub(r'["“”«»]', ' ', cleaned)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        cleaned = re.sub(r'\s+([,.!?])', r'\1', cleaned)
        cleaned = cleaned.strip()

        # Clean trailing dot artifact from quotes: e.g. 'ngon quá!.' -> 'ngon quá!'
        cleaned = re.sub(r'([!?])\s*\.\s*$', r'\1', cleaned)

        return cleaned.strip()

    @classmethod
    def _fallback_dialogue_blocks(cls, lines: List[str]) -> tuple[List[str], str]:
        """Select likely spoken copy without inventing or rewriting text."""
        quoted_blocks: List[str] = []
        plain_blocks: List[str] = []
        has_script_context = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            quoted = cls.QUOTED_SPAN_PATTERN.findall(stripped)
            if quoted:
                for item in quoted:
                    cleaned = cls._clean_spoken_text(item)
                    if cleaned:
                        quoted_blocks.append(cleaned)
                continue

            if cls.PURE_PARENTHETICAL_PATTERN.match(stripped):
                continue

            if cls.SCRIPT_HEADER_PATTERN.match(stripped) or cls.SCENE_OR_TIMESTAMP_PATTERN.match(stripped):
                has_script_context = True
                continue

            if cls.PRODUCTION_INSTRUCTION_HEADER_PATTERN.match(stripped):
                has_script_context = True
                continue

            if cls.MD_HEADER_PATTERN.match(stripped):
                has_script_context = True
                continue

            # A labelled line without quotes is metadata unless it has already
            # matched the explicit dialogue path above.
            if re.match(r'^[\s*\-•\d.]*[A-Za-zÀ-ỹ\s0-9/_\-]+\s*:', stripped):
                continue

            cleaned = cls._clean_spoken_text(cls.MD_BULLET_PREFIX_PATTERN.sub('', stripped))
            if cleaned:
                plain_blocks.append(cleaned)

        if quoted_blocks:
            return quoted_blocks, "success"
        if has_script_context and len(plain_blocks) >= 2:
            return plain_blocks, "uncertain"
        return [], "no_dialogue"

    @classmethod
    def extract(cls, raw_text: str) -> ExtractionResult:
        """
        Main extraction routine:
        1. Identifies lines explicitly matching dialogue markers.
        2. Strictly stops dialogue capture when encountering production instruction headers.
        3. Normalizes spoken dialogue into clean sentences in sequential order.
        4. If no dialogue markers exist:
           - Checks if raw text is a pure short monologue without any production headers.
           - Otherwise flags as 'no_dialogue' so full raw analysis is NEVER pushed to TTS.
        """
        if not raw_text or not raw_text.strip():
            return ExtractionResult(
                cleaned_script="",
                original_length=0,
                cleaned_length=0,
                dialogue_blocks_count=0,
                status="no_dialogue",
                warning_message="Văn bản kịch bản trống."
            )

        original_len = len(raw_text)
        lines = raw_text.splitlines()

        extracted_dialogue_blocks = []
        is_in_dialogue_block = False
        current_block_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if is_in_dialogue_block and current_block_lines:
                    # Preserve natural paragraph pause in multi-line speech
                    current_block_lines.append("")
                continue

            # Check if this line is a dialogue marker
            dialogue_match = cls.DIALOGUE_LINE_PATTERN.match(stripped)
            if dialogue_match:
                if current_block_lines:
                    raw_block = " ".join([l for l in current_block_lines if l]).strip()
                    cleaned_block = cls._clean_spoken_text(raw_block)
                    if cleaned_block:
                        extracted_dialogue_blocks.append(cleaned_block)
                    current_block_lines = []

                is_in_dialogue_block = True
                content = dialogue_match.group(1).strip()
                if content:
                    current_block_lines.append(content)
                continue

            # Check if this line is a production instruction header, scene delimiter, or a new labeled item
            prod_match = cls.PRODUCTION_INSTRUCTION_HEADER_PATTERN.match(stripped)
            scene_match = cls.SCENE_OR_TIMESTAMP_PATTERN.match(stripped)
            is_labeled_item = bool(re.match(r'^[\s*\-•\d.]*\s*(?:\*\*)?[A-Za-zÀ-ỹ\s0-9/_\-]+(?:\*\*)?\s*:', stripped))

            if prod_match or scene_match or (is_in_dialogue_block and is_labeled_item):
                if is_in_dialogue_block and current_block_lines:
                    raw_block = " ".join([l for l in current_block_lines if l]).strip()
                    cleaned_block = cls._clean_spoken_text(raw_block)
                    if cleaned_block:
                        extracted_dialogue_blocks.append(cleaned_block)
                    current_block_lines = []
                is_in_dialogue_block = False
                continue

            # If inside an ongoing dialogue block, keep collecting continuation lines (wrapped text or sub-bullet speech)
            if is_in_dialogue_block:
                clean_line = cls.MD_BULLET_PREFIX_PATTERN.sub('', stripped).strip()
                if clean_line:
                    current_block_lines.append(clean_line)

        # Flush trailing block
        if is_in_dialogue_block and current_block_lines:
            raw_block = " ".join([l for l in current_block_lines if l]).strip()
            cleaned_block = cls._clean_spoken_text(raw_block)
            if cleaned_block:
                extracted_dialogue_blocks.append(cleaned_block)

        # Filter out empty blocks
        final_blocks = [b for b in extracted_dialogue_blocks if b.strip()]

        # Case A: Explicit dialogue blocks successfully found
        if final_blocks:
            final_text = "\n\n".join(final_blocks)
            return ExtractionResult(
                cleaned_script=final_text,
                original_length=original_len,
                cleaned_length=len(final_text),
                dialogue_blocks_count=len(final_blocks),
                status="success",
                extracted_blocks=final_blocks
            )

        # Case B: No explicit dialogue markers found. Use a conservative
        # deterministic fallback for naturally written multi-part scripts.
        fallback_blocks, fallback_status = cls._fallback_dialogue_blocks(lines)
        if fallback_blocks:
            final_text = "\n\n".join(fallback_blocks)
            return ExtractionResult(
                cleaned_script=final_text,
                original_length=original_len,
                cleaned_length=len(final_text),
                dialogue_blocks_count=len(fallback_blocks),
                status=fallback_status,
                warning_message=(
                    "Hệ thống đã nhận diện các đoạn có khả năng là lời thoại. "
                    "Vui lòng kiểm tra trước khi tạo audio."
                    if fallback_status == "uncertain"
                    else None
                ),
                extracted_blocks=fallback_blocks,
            )

        # Guardrail: Check if the text is a structured response (marketing analysis, storyboard, production cues)
        has_structure = (
            bool(cls.PRODUCTION_INSTRUCTION_HEADER_PATTERN.search(raw_text)) or
            bool(cls.MD_HEADER_PATTERN.search(raw_text)) or
            bool(cls.SCENE_OR_TIMESTAMP_PATTERN.search(raw_text)) or
            len([l for l in lines if cls.BULLET_ITEM_START_PATTERN.match(l.strip())]) >= 2 or
            len(lines) > 4
        )

        if has_structure:
            # The AI response is a technical outline, marketing plan, or strategy without dialogue markers.
            # Strictly return blank cleaned_script with "no_dialogue" status.
            return ExtractionResult(
                cleaned_script="",
                original_length=original_len,
                cleaned_length=0,
                dialogue_blocks_count=0,
                status="no_dialogue",
                warning_message=(
                    "Không tìm thấy cấu trúc lời thoại (VO / Lời thoại / Narration) trong kịch bản. "
                    "Hệ thống đã để trống để bạn nhập hoặc dán nội dung cần đọc."
                )
            )

        # Case C: The text is a very short, plain, unstructured text (possible direct monologue)
        cleaned_plain = cls._clean_spoken_text(raw_text)
        cleaned_plain = cls.MD_HEADER_PATTERN.sub('', cleaned_plain)
        cleaned_plain = cls.MD_BLOCKQUOTE_PATTERN.sub('', cleaned_plain)
        cleaned_plain = cls.MD_FORMATTING_PATTERN.sub('', cleaned_plain)

        lines_cleaned = [cls.MD_BULLET_PREFIX_PATTERN.sub('', l.strip()).strip() for l in cleaned_plain.splitlines()]
        cleaned_plain = "\n\n".join([l for l in lines_cleaned if l])

        return ExtractionResult(
            cleaned_script=cleaned_plain,
            original_length=original_len,
            cleaned_length=len(cleaned_plain),
            dialogue_blocks_count=1 if cleaned_plain else 0,
            status="uncertain" if cleaned_plain else "no_dialogue",
            warning_message=(
                "Văn bản không có nhãn phân cảnh hoặc lời thoại rõ ràng. "
                "Vui lòng kiểm tra lại nội dung trước khi tạo audio."
            ) if cleaned_plain else "Không tìm thấy nội dung lời thoại."
        )
