import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, Set

import yaml
from src.core.config import get_settings
from src.schemas.judge import JudgeResult
from src.schemas.policy import Policy

# 로깅 설정
logger = logging.getLogger(__name__)

class JudgeEngine:
    """
    [Final Optimized Version] 
    - 정책 기반 동적 판정 및 액션 결정 엔진
    - 데이터 캐싱을 통한 성능 최적화
    - 심각도(Severity) 및 신뢰도 기반 차등 액션 적용
    """
    
    # 하위 호환성을 위한 기본 카테고리 매핑
    DEFAULT_CATEGORY_MAPPING = {
        "HAL": "groundedness",
        "CONTENT": "content_safety",
        "CTX": "instruction_compliance",
        "FORMAT": "instruction_compliance"
    }

    def __init__(self, prompt_dir: str | None = None, llm_client=None):
        self.prompt_dir = Path(prompt_dir or get_settings().prompt_dir)
        self.llm_client = llm_client
        self._prompt_cache: Dict[str, str] = {}
        self._few_shot_cache: Dict[str, Any] = {}

    def _read_prompt(self, name: str) -> str:
        """프롬프트 파일을 읽고 캐싱합니다."""
        if name in self._prompt_cache:
            return self._prompt_cache[name]
        
        path = self.prompt_dir / name
        if not path.exists():
            logger.warning(f"Prompt file not found: {path}")
            return ""
        
        content = path.read_text(encoding="utf-8")
        self._prompt_cache[name] = content
        return content

    def _get_filtered_few_shot(self, policy: Policy) -> str:
        """
        [최적화] 정책 카테고리에 맞는 Few-shot 예시를 필터링합니다.
        """
        category = policy.category or ""
        
        # 1. 예시 데이터 로드 및 캐싱
        if "few_shot_examples_v2.yaml" not in self._few_shot_cache:
            full_content = self._read_prompt("few_shot_examples_v2.yaml")
            if not full_content:
                return ""
            try:
                self._few_shot_cache["few_shot_examples_v2.yaml"] = yaml.safe_load(full_content).get("examples", {})
            except Exception as e:
                logger.error(f"Error parsing few-shot YAML: {e}")
                return ""

        all_examples = self._few_shot_cache["few_shot_examples_v2.yaml"]
        filtered_examples = {}

        # 2. 매칭 타겟 결정 (카테고리 -> ID 프리픽스 순)
        target_prefix = category.lower()
        if not target_prefix:
            for prefix, mapped_cat in self.DEFAULT_CATEGORY_MAPPING.items():
                if prefix in policy.id.upper():
                    target_prefix = mapped_cat
                    break

        # 3. 필터링 수행
        if target_prefix:
            for key, val in all_examples.items():
                if key.startswith(target_prefix):
                    filtered_examples[key] = val

        if not filtered_examples:
            return "No relevant few-shot examples found."

        return yaml.dump({"examples": filtered_examples}, allow_unicode=True, sort_keys=False)

    def _extract_judged_text(self, response: str) -> str:
        """JSON 응답인 경우 본문 텍스트만 추출합니다.

        [수정 이유] 기존에는 "answer" 키만 추출했으나, 현재 응답 포맷이
        summary / evidence / disclaimer 구조로 변경됨에 따라 "summary" 키를
        우선 추출하도록 수정. "answer" 키는 하위 호환성을 위해 유지.
        두 키 모두 없으면 response 전체를 반환하는 기존 동작을 그대로 유지.
        """
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                for key in ("summary", "answer"):
                    if key in parsed:
                        return str(parsed[key]).strip()
        except (json.JSONDecodeError, TypeError):
            pass
        return response.strip()

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        """구두점을 제거한 뒤 단어 집합을 반환합니다 (한국어/영어 공통).

        [수정 이유] 기존 fallback은 응답 전체 문자열이 컨텍스트에 완전히 포함되는지를
        확인했으나(judged_text in context_text), 자연어 응답은 표현이 조금만 달라도
        항상 FAIL로 판정되는 문제가 있었음. 구두점 제거 후 토큰 단위로 비교하면
        한국어·영어 모두에서 의미 있는 유사도를 측정할 수 있음.
        """
        return {t for t in re.sub(r'[^\w\s]', '', text).split() if len(t) > 1}

    def _judge_groundedness_fallback(self, response: str, retrieved_context: list[str] | None) -> JudgeResult:
        """LLM 장애 시 토큰 중복 비율 기반의 Fallback 환각 판정 로직입니다.

        [수정 이유] 기존 단순 문자열 포함 검사(in 연산자)에서 토큰 중복 비율 방식으로 교체.
        응답 토큰의 30% 이상이 컨텍스트 토큰과 겹치면 PASS로 처리하며,
        신뢰도는 중복 비율에 비례해 0.5~0.9 범위로 산출함.
        """
        judged_text = self._extract_judged_text(response)

        if not retrieved_context or not any(str(c).strip() for c in retrieved_context):
            return JudgeResult(
                verdict="FAIL", confidence=0.6,
                reason="No context provided for grounding check.",
                evidence_text=judged_text[:100],
            )

        context_text = " ".join(str(c) for c in retrieved_context)
        response_tokens = self._tokenize(judged_text)
        context_tokens = self._tokenize(context_text)

        if response_tokens:
            overlap = response_tokens & context_tokens
            overlap_ratio = len(overlap) / len(response_tokens)
            # 응답 토큰의 30% 이상이 컨텍스트에 존재하면 근거 있음으로 판정
            if overlap_ratio >= 0.3:
                return JudgeResult(
                    verdict="PASS",
                    confidence=min(0.5 + overlap_ratio * 0.4, 0.9),
                    reason=f"Response is supported by context (Fallback, overlap: {overlap_ratio:.0%})",
                )

        return JudgeResult(
            verdict="FAIL", confidence=0.7,
            reason="Response tokens not sufficiently found in context (Fallback)",
            evidence_text=judged_text[:100],
        )

    def _parse_llm_json_result(self, raw_llm_output: str | None) -> JudgeResult | None:
        """LLM 출력에서 JSON을 추출하고 JudgeResult로 파싱합니다."""
        if not raw_llm_output:
            return None

        json_match = re.search(r"\{.*\}", raw_llm_output, re.DOTALL)
        if not json_match:
            return None

        try:
            parsed = json.loads(json_match.group())
            return JudgeResult(**parsed)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(f"JSON parsing error: {e}")
            return JudgeResult(
                verdict="FAIL", confidence=0.0,
                reason=f"Failed to parse LLM output: {str(e)}",
                evidence_text=raw_llm_output[:100]
            )

    def _determine_action_by_severity(self, result: JudgeResult, policy: Policy) -> JudgeResult:
        """판정 결과와 정책 메타데이터를 기반으로 최종 Action을 결정합니다.

        [수정 이유 1 — 원본 불변] 기존 코드는 파라미터로 받은 result 객체의 필드를
        직접 수정(in-place mutation)했음. 호출자가 원본 JudgeResult를 보유하고 있을 때
        예상치 못한 사이드이펙트가 발생할 수 있으므로 model_copy()로 복사 후 수정.

        [수정 이유 2 — category 우선순위] 기존 조건문은 category와 policy.id를 OR로
        결합했기 때문에, category="groundedness"이지만 id에 "CONTENT"가 포함된 경우
        content_safety 분기로 잘못 진입하는 버그가 있었음.
        category가 명시된 경우 항상 category를 우선 적용하고,
        category가 없을 때만 id 프리픽스를 fallback으로 사용하도록 재구성.

        [수정 이유 3 — action.type None 안전 처리] PolicyAction.action.type은
        Optional 필드이므로 None일 수 있음. 기존 코드는 None을 그대로 대입할 수
        있었으므로 "Retry" 기본값으로 보호.
        """
        # [수정 1] 원본 result를 직접 수정하지 않기 위해 복사본을 만들어 사용
        result = result.model_copy()

        if result.verdict == "PASS":
            result.severity = "Safe"
            result.action = "Allow"
            return result

        category = policy.category or ""

        # [수정 2] category가 명시된 경우 category 우선 판단, 미설정 시 id 프리픽스로 추론.
        # "CONTENT_001"처럼 id에 여러 의미가 섞인 경우에도 category 기반 분기로 정확히 진입.

        # 1. 고위험 정책 (유해성 등) -> 무조건 차단
        if "content_safety" in category or ("CONTENT" in policy.id and not category):
            result.severity = "Critical"
            result.action = "Block"
            result.reason = f"[Critical Violation] {result.reason}"

        # 2. 신뢰도 기반 정책 (환각 등) -> 임계치에 따른 차등 처리
        elif "groundedness" in category or ("HAL" in policy.id and not category):
            threshold = 0.6
            if policy.severity_by_confidence:
                threshold = policy.severity_by_confidence.high_when_confidence_gte or threshold

            if result.confidence < threshold:
                result.severity = "Critical"
                result.action = "Block"
                result.reason = f"[Hallucination Detected] {result.reason}"
            else:
                result.severity = "Warning"
                result.action = "Retry"
                result.reason = f"[Groundedness Check Failed] {result.reason}"

        # 3. 기타 (형식, 지침 등) -> 정책 설정에 따름
        else:
            result.severity = policy.severity.upper() if policy.severity else "Warning"
            # [수정 3] action.type은 Optional이므로 None인 경우 "Retry"로 안전 처리
            result.action = (policy.action.type if policy.action and policy.action.type else None) or "Retry"

        return result

    def judge(
        self,
        policy: Policy,
        response: str,
        retrieved_context: list[str] | None,
        query: str = "",
        current_retry: int = 0
    ) -> JudgeResult:
        """정책별 최적화된 프롬프트를 사용하여 응답의 적절성을 판정합니다."""
        
        # 1. 프롬프트 구성
        system_tmpl = self._read_prompt("system_judge_v2.txt")
        cot_tmpl = self._read_prompt("cot_reasoning_v2.txt")
        few_shot_str = self._get_filtered_few_shot(policy)
        
        context_info = f"Policy Name: {policy.name}\nCategory: {policy.category or 'General'}"
        
        # [수정] few_shot_str은 yaml.dump() 결과물이므로 예시 데이터 안에 "{", "}" 문자가
        # 포함될 수 있음. 이 상태에서 str.format()을 호출하면 해당 중괄호를 플레이스홀더로
        # 잘못 인식하여 KeyError가 발생. 이스케이프({{ }})로 리터럴 문자로 변환한 뒤 연결.
        safe_few_shot = few_shot_str.replace("{", "{{").replace("}", "}}")
        rendered_prompt = f"{system_tmpl}\n\n{context_info}\n\n{cot_tmpl}\n\n{safe_few_shot}".format(
            user_query=query,
            retrieved_context="\n".join(retrieved_context) if retrieved_context else "N/A",
            assistant_response=response,
            criteria=policy.judge.criteria or "No specific criteria defined. Apply general safety evaluation.",
        )

        # 2. LLM 호출
        raw_llm_output = None
        if self.llm_client:
            try:
                raw_llm_output = self.llm_client.invoke(rendered_prompt).content
            except Exception as e:
                logger.error(f"LLM invocation error: {e}")

        # 3. 결과 분석 및 Fallback
        parsed_result = self._parse_llm_json_result(raw_llm_output)

        if not parsed_result:
            category = policy.category or ""
            if policy.preconditions and policy.preconditions.requires_retrieved_context:
                # 컨텍스트 기반 검증이 필요한 경우: 토큰 중복 비율 Fallback 실행
                parsed_result = self._judge_groundedness_fallback(response, retrieved_context)
            elif "content_safety" in category or "CONTENT" in policy.id:
                # 유해성 정책은 LLM 장애 시 안전 우선(Fail-safe) 처리.
                # LLM이 응답 불능일 때 PASS를 반환하면 실제 유해 콘텐츠가 그대로 통과할 수 있음.
                parsed_result = JudgeResult(
                    verdict="FAIL", confidence=1.0,
                    reason="LLM parsing failed. Content safety policy defaults to FAIL (Fail-safe fallback).",
                )
            elif "instruction_compliance" in category or "CTX" in policy.id:
                # [수정] CTX_001 등 지침 준수 정책은 parse 실패 시 PASS로 흘러
                # 실제 위반이 감지되지 않는 문제가 있었음. 안전 우선 원칙에 따라 FAIL로 처리.
                parsed_result = JudgeResult(
                    verdict="FAIL", confidence=0.5,
                    reason="LLM parsing failed. Instruction compliance policy defaults to FAIL (Fail-safe fallback).",
                )
            else:
                # 그 외 정책은 오탐(False Positive) 방지를 위해 PASS로 처리
                parsed_result = JudgeResult(
                    verdict="PASS", confidence=0.5,
                    reason="Pass due to LLM judgment failure (Safe-side fallback).",
                )

        # 4. 최종 액션 결정
        final_result = self._determine_action_by_severity(parsed_result, policy)

        # 5. 재시도 초과 시 강제 차단 (안전장치)
        if final_result.action == "Retry" and current_retry >= 3:
            final_result.action = "Block"
            final_result.severity = "Critical"
            final_result.reason = f"[Max Retries Exceeded] {final_result.reason}"

        return final_result