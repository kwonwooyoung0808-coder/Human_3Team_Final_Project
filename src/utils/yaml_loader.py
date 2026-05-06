import logging
from pathlib import Path
from typing import List, Union

import yaml
from pydantic import ValidationError

from src.schemas.policy import Policy

# 모듈 단위 로거 설정
logger = logging.getLogger(__name__)

class PolicyLoaderError(Exception):
    pass

def load_policy(path: Union[str, Path]) -> Policy:
    """
    단일 YAML 파일을 읽어 Policy 객체로 변환
    Pydantic의 model_validate를 사용하여 누락된 필드나 타입 오류 등 데이터 유효성 검증

    Args:
        path (Union[str, Path]): 로드할 YAML 파일의 경로

    Returns:
        Policy: 검증이 완료된 정책 객체

    Raises:
        PolicyLoaderError: 파일 미존재, 빈 파일, 잘못된 YAML 문법, 또는 스키마 검증 실패 시 발생
    """
    path_obj = Path(path)

    if not path_obj.exists():
        raise PolicyLoaderError(f"Policy file not found: {path_obj}")

    try:
        with path_obj.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        if data is None:
            raise PolicyLoaderError(f"Policy file is empty: {path_obj.name}")

        # 파싱된 데이터를 바탕으로 Pydantic 스키마 유효성 검증
        return Policy.model_validate(data)

    except yaml.YAMLError as exc:
        raise PolicyLoaderError(f"Invalid YAML syntax in '{path_obj.name}': {exc}")
    except ValidationError as exc:
        # 스키마 검증 실패 시 디버깅을 용이하게 하기 위해 상세 에러 내역 포함
        error_detail = exc.errors()
        raise PolicyLoaderError(f"Schema validation failed for '{path_obj.name}': {error_detail}")
    except Exception as exc:
        raise PolicyLoaderError(f"Unexpected error loading '{path_obj.name}': {exc}")

def load_policies(policy_dir: Union[str, Path]) -> List[Policy]:
    """
    지정된 디렉토리 내의 모든 *.yaml 정책 파일 로드
    활성화된(enabled=True) 정책만 필터링하며, 반환되는 리스트는 우선순위(priority)를 기준으로 내림차순 정렬

    Args:
        policy_dir (Union[str, Path]): 정책 파일들이 위치한 디렉토리 경로

    Returns:
        List[Policy]: 유효성 검증 및 정렬이 완료된 활성화 정책 객체 리스트
    """
    policies: List[Policy] = []
    base_path = Path(policy_dir)

    if not base_path.exists() or not base_path.is_dir():
        logger.warning(f"Policy directory does not exist: {policy_dir}")
        return policies

    # 대상 디렉토리 내의 모든 YAML 파일 순회
    for path in base_path.glob("*.yaml"):
        try:
            policy = load_policy(path)
            if policy.enabled:
                policies.append(policy)
        except PolicyLoaderError as e:
            # 개별 정책 파일 로딩 실패가 전체 시스템 장애로 전파되지 않도록 로깅 후 다음 파일 진행
            logger.error(e)
            continue

    # 정책 엔진 실행 순서 보장을 위해 priority 기준 내림차순 정렬 (높은 값이 먼저 실행됨)
    policies.sort(key=lambda p: p.priority, reverse=True)

    return policies
