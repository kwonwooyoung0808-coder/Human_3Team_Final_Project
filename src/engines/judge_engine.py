import re
import json
import yaml
from pathlib import Path

from src.core.config import get_settings
from src.schemas.judge import JudgeResult
from src.schemas.policy import Policy


class JudgeEngine:
    def __init__(self, prompt_dir: str | None = None):
        self.prompt_dir = Path(prompt_dir or get_settings().prompt_dir)

    def _read_prompt(self, name: str) -> str:
        path = self.prompt_dir / name
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _get_filtered_few_shot(self, policy_id: str) -> str:
        """
        정책 ID에 발맞춰 필요한 Few-shot 예시만 필터링하여 반환합니다.
        """
        full_content = self._read_prompt("few_shot_examples_v2.yaml")
        if not full_content:
            return ""
            
        try:
            data = yaml.safe_load(full_content)
            all_examples = data.get("examples", {})
            filtered_examples = {}

            # 정책 ID 기반 필터링 매핑
            if "CONTENT" in policy_id:
                target_key_prefix = "content_safety"
            elif "GROUND" in policy_id:
                target_key_prefix = "groundedness"
            elif "COMP" in policy_id:
                target_key_prefix = "instruction_compliance"
            else:
                target_key_prefix = "none"

            for key, val in all_examples.items():
                if key.startswith(target_key_prefix):
                    filtered_examples[key] = val

            if not filtered_examples:
                return "No relevant few-shot examples found."

            # YAML 형태로 다시 덤프 (프롬프트 주입용)
            return yaml.dump({"examples": filtered_examples}, allow_unicode=True, sort_keys=False)
        except Exception:
            return "Error parsing few-shot examples."

    def judge(self, policy: Policy, response: str, retrieved_context: list[str] | None, query: str = "") -> JudgeResult:
        """
        시스템 프롬프트, CoT 추론 가이드, Few-shot 예시를 결합하여 하나의 완성된 프롬프트를 생성하고 평가를 수행합니다.
        """
        # 1. 개별 프롬프트 파일 로드 및 필터링
        system_tmpl = self._read_prompt("system_judge_v2.txt")
        cot_tmpl = self._read_prompt("cot_reasoning_v2.txt")
        few_shot_str = self._get_filtered_few_shot(policy.id)

        # 2. 프롬프트 결합 (Concatenate)
        full_prompt_template = f"{system_tmpl}\n\n{cot_tmpl}\n\n{few_shot_str}"

        # 3. 데이터 준비 및 예약어 치환 (Dynamic Injection)
        criteria = policy.judge.criteria or "No specific criteria provided. Use general safety guidelines."
        
        # B-4 연관: 컨텍스트 부재 시 "해당 없음" 처리
        context_str = "\n".join(retrieved_context) if retrieved_context else "해당 없음 (Context not required or absent)"

        rendered_prompt = full_prompt_template.format(
            user_query=query,
            retrieved_context=context_str,
            assistant_response=response,
            criteria=criteria
        )

        # [TODO] 실제 LLM API 호출 (예: openai.ChatCompletion.create)
        # 4. LLM 응답 시뮬레이션 및 Post-processing (Regex 기반 JSON 추출)
        # 아래는 LLM 응답 예시입니다 (실제로는 API 호출 결과가 오게 됨)
        mock_raw_llm_output = '주장하신 내용을 분석한 결과입니다. ```json {"verdict": "PASS", "confidence": 0.8, "reason": "정상적인 정보 제공성 응답입니다.", "evidence_text": null} ``` 수고하세요.'

        # 정규표현식으로 { } 사이의 JSON 내용만 추출
        json_match = re.search(r"\{.*\}", mock_raw_llm_output, re.DOTALL)
        if json_match:
            try:
                parsed_result = json.loads(json_match.group())
                return JudgeResult(**parsed_result)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                # 파싱 실패 시 기본 에러 결과 반환
                return JudgeResult(
                    verdict="FAIL",
                    confidence=0.0,
                    reason=f"Failed to parse LLM output: {str(e)}",
                    evidence_text=mock_raw_llm_output[:100]
                )

        # 기본 Mockup (정책 ID 기반 기존 로직 유지용 - 레거시 대응)
        if policy.id == "GROUND_001":
            if not retrieved_context:
                return JudgeResult(
                    verdict="FAIL",
                    confidence=0.65,
                    reason="No retrieved context was provided.",
                    evidence_text=response[:120],
                )
            # ... (기타 레거시 매칭 로직) ...

        return JudgeResult(
            verdict="PASS",
            confidence=0.7,
            reason="No additional judge-only violation was detected (Fallback).",
            evidence_text=None,
        )
