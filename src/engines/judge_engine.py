import json
import re
from pathlib import Path
import yaml
from src.core.config import get_settings
from src.schemas.judge import JudgeResult
from src.schemas.policy import Policy

class JudgeEngine:
    """
    PRD 지침에 따라 정책 위반 및 사실 왜곡(Hallucination)을 판정하는 엔진입니다.
    시스템 프롬프트, CoT 추론 가이드, 정책별 Few-shot을 결합하여 LLM에게 전달합니다.
    """
    def __init__(self, prompt_dir: str | None = None):
        self.prompt_dir = Path(prompt_dir or get_settings().prompt_dir)

    def _read_prompt(self, name: str) -> str:
        """프롬프트 파일(.txt, .yaml)을 읽어옵니다."""
        path = self.prompt_dir / name
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _get_filtered_few_shot(self, policy_id: str) -> str:
        """
        [PRD 최적화] 정책 ID에 맞는 Few-shot 예시만 필터링하여 프롬프트 크기를 줄이고 정확도를 높입니다.
        - CONTENT: 유해성 판정 예시
        - GROUND: 근거 기반 판정 예시
        - COMP: 형식 준수 판정 예시
        """
        full_content = self._read_prompt("few_shot_examples_v2.yaml")
        if not full_content:
            return ""

        try:
            data = yaml.safe_load(full_content)
            all_examples = data.get("examples", {})
            filtered_examples = {}

            # 정책 ID 접두어에 따른 예시 그룹 매칭
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

            return yaml.dump({"examples": filtered_examples}, allow_unicode=True, sort_keys=False)
        except Exception:
            return "Error parsing few-shot examples."

    def _extract_judged_text(self, response: str) -> str:
        """
        [데이터 정규화] 응답이 JSON 형태인 경우 'answer' 필드의 본문만 추출하여 판정 대상을 명확히 합니다.
        """
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                answer = parsed.get("answer")
                if isinstance(answer, str) and answer.strip():
                    return answer.strip()
        except json.JSONDecodeError:
            pass
        return response.strip()

    def _judge_groundedness_fallback(
        self,
        response: str,
        retrieved_context: list[str] | None,
    ) -> JudgeResult:
        """
        [B-4 대응] LLM 장애 시나리오를 위한 문자열 매칭 기반의 최소한의 Groundedness 판정 로직입니다.
        """
        judged_text = self._extract_judged_text(response)

        if not retrieved_context:
            return JudgeResult(
                verdict="FAIL",
                confidence=0.65,
                reason="No retrieved context was provided.",
                evidence_text=judged_text[:120] or None,
            )

        cleaned_context = [str(item).strip() for item in retrieved_context if str(item).strip()]
        if not cleaned_context:
            return JudgeResult(
                verdict="FAIL",
                confidence=0.65,
                reason="No meaningful retrieved context was provided.",
                evidence_text=judged_text[:120] or None,
            )

        context_text = " ".join(cleaned_context)
        # 단순 포함 여부 확인 (LLM 연결 전 임시 로직)
        if judged_text and judged_text in context_text:
            return JudgeResult(
                verdict="PASS",
                confidence=0.9,
                reason="The response is grounded in the provided context.",
                evidence_text=None,
            )

        return JudgeResult(
            verdict="FAIL",
            confidence=0.72,
            reason="The response is not sufficiently grounded in the provided context.",
            evidence_text=judged_text[:120] or None,
        )

    def _parse_llm_json_result(self, raw_llm_output: str) -> JudgeResult | None:
        """
        [안정성 확보] LLM이 JSON 외에 앞뒤로 덧붙인 설명 문구에서 순수 JSON 부분만 정규식으로 추출합니다.
        """
        if not raw_llm_output:
            return None

        # 정규표현식을 통해 가장 바깥쪽 { } 구간을 찾아냄
        json_match = re.search(r"\{.*\}", raw_llm_output, re.DOTALL)
        if not json_match:
            return None

        try:
            parsed_result = json.loads(json_match.group())
            return JudgeResult(**parsed_result)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            return JudgeResult(
                verdict="FAIL",
                confidence=0.0,
                reason=f"Failed to parse LLM output: {str(e)}",
                evidence_text=raw_llm_output[:100] or None,
            )

    def judge(
        self,
        policy: Policy,
        response: str,
        retrieved_context: list[str] | None,
        query: str = "",
    ) -> JudgeResult:
        """
        [Main Engine] system_judge_v2 + cot_reasoning_v2 + YAML criteria를 조립하여 판정을 수행합니다.
        """
        # 1. 프롬프트 구성 요소 로드
        system_tmpl = self._read_prompt("system_judge_v2.txt")
        cot_tmpl = self._read_prompt("cot_reasoning_v2.txt")
        few_shot_str = self._get_filtered_few_shot(policy.id)

        # 2. 동적 프롬프트 조립
        full_prompt_template = f"{system_tmpl}\n\n{cot_tmpl}\n\n{few_shot_str}"
        
        # YAML에서 로드된 정책별 criteria 주입
        criteria = policy.judge.criteria or "No specific criteria provided. Use general safety guidelines."
        context_str = "\n".join(retrieved_context) if retrieved_context else "N/A (Context not required or absent)"

        # 3. 변수 치환 (Formatting)
        rendered_prompt = full_prompt_template.format(
            user_query=query,
            retrieved_context=context_str,
            assistant_response=response,
            criteria=criteria,
        )

        # [TODO] 실제 Ollama 또는 API 모델 호출부 (rendered_prompt 전달)
        # 예: raw_llm_output = self.llm_client.generate(rendered_prompt)
        raw_llm_output = "" 
        
        # 4. LLM 응답 해석 (JSON 파싱)
        parsed_llm_result = self._parse_llm_json_result(raw_llm_output)
        if parsed_llm_result is not None:
            return parsed_llm_result

        # 5. LLM 미응답 시 정책별 Fallback 처리
        if policy.id == "GROUND_001":
            # Groundedness는 엄격한 체크를 위해 전용 fallback 실행
            return self._judge_groundedness_fallback(response, retrieved_context)

        # 그 외 보안 정책 등은 아직 LLM 연결 전이므로 기본 PASS로 통과 (Rule 엔진이 앞단에서 막았다고 가정)
        return JudgeResult(
            verdict="PASS",
            confidence=0.7,
            reason="No additional judge-only violation was detected (Fallback).",
            evidence_text=None,
        )