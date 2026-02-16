# ┌───────────────────────────────────────────────────────────────┐
# │  Copyright (c) 2025 Ateet Vatan Bahmani                      │
# │  Project: MASX AI – Strategic Agentic AI System              │
# │  All rights reserved.                                        │
# └───────────────────────────────────────────────────────────────┘
#
# MASX AI is a proprietary software system developed and owned by Ateet Vatan Bahmani.
# The source code, documentation, workflows, designs, and naming (including "MASX AI")
# are protected by applicable copyright and trademark laws.
#
# Redistribution, modification, commercial use, or publication of any portion of this
# project without explicit written consent is strictly prohibited.
#
# This project is not open-source and is intended solely for internal, research,
# or demonstration use by the author.
#
# Contact: ab@masxai.com | MASXAI.com

"""
Flashpoint LLM Agent Validator for MASX-HOTSPOTS Agentic AI System.

Checks if the flashpoint belongs to the accepted strategic domains.

Usage: from app.agents.flashpoint_validator_agent import FlashpointValidatorAgent
    agent = FlashpointValidatorAgent()
"""

# flashpoint_validator_agent.py

from typing import Dict, Any, List
from pydantic import BaseModel, ValidationError

from ..core.flashpoint import FlashpointItem, FlashpointDataset
from ..constants import DOMAIN_CATEGORIES
from ..services.llm_service import LLMService
from ..config.logging_config import get_logger
from ..core.utils import safe_json_loads
from ..core.state import AgentState
from ..core.exceptions import AgentException
from .base import BaseAgent, AgentResult
from ..core.utils import safe_json_loads


class FlashpointValidationResponse(BaseModel):
    decision: str  # 'yes' or 'no'

    @classmethod
    def validate_decision(cls, value: str) -> bool:
        return value.strip().lower() in {"yes", "no"}


class FlashpointValidatorAgent(BaseAgent):
    """
    Agent to validate if each flashpoint belongs to accepted strategic domains,
    using both symbolic filtering and deterministic LLM classification.
    """

    def __init__(self):
        super().__init__(
            name="flashpoint_validator_agent",
            description="Validates flashpoints using domain keywords + LLM classification",
        )
        self.logger = get_logger(__name__)
        self.llm_service = LLMService.get_instance()  # singleton
        self.keywords = self._extract_keywords(DOMAIN_CATEGORIES)

    def _extract_keywords(self, domains: List[str]) -> List[str]:
        keywords = set()
        for domain in domains:
            for word in domain.lower().replace("/", " ").replace("-", " ").split():
                keywords.add(word.strip())
        return list(keywords)

    @property
    def SYSTEM_PROMPT(self) -> str:
        return (
            "You are a geopolitical domain classifier.\n"
            "Your task is to classify a flashpoint as either 'yes' or 'no' based on the following domains:\n\n"
            + "\n".join(f"- {domain}" for domain in DOMAIN_CATEGORIES)
            + "\n\nOnly respond in **valid JSON** format like this:\n"
            '{ "decision": "yes" }\n'
            "or\n"
            '{ "decision": "no" }\n\n'
            "Do not include any explanation, notes, or extra text."
        )

    def _build_user_prompt(self, fp: FlashpointItem) -> str:
        return (
            f"Flashpoint:\n"
            f"Title: {fp.title}\n"
            f"Description: {fp.description}\n"
            f"Entities: {', '.join(fp.entities)}\n\n"
            "Does this flashpoint clearly relate to the domains above?"
        )

    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        try:
            flashpoints: FlashpointDataset = input_data["flashpoints"]
            valid_flashpoints, unrelated = [], []

            for fp in flashpoints:
                # LLM validation (temp = 0)
                prompt = self._build_user_prompt(fp)
                llm_output = (
                    self.llm_service.generate_text(
                        user_prompt=prompt,
                        system_prompt=self.SYSTEM_PROMPT,
                        temperature=0.0,
                        max_tokens=100,
                    )
                    .strip()
                    .lower()
                )

                try:
                    parsed = FlashpointValidationResponse.model_validate(
                        safe_json_loads(llm_output)
                    )
                    decision = parsed.decision.lower()
                except (ValidationError, ValueError) as ve:
                    self.logger.warning(f"Invalid LLM output: {llm_output}")
                    unrelated.append(fp)
                    continue

                if decision == "yes":
                    valid_flashpoints.append(fp)
                else:
                    unrelated.append(fp)

            return AgentResult(
                success=True,
                data={"flashpoints": valid_flashpoints, "unrelated": unrelated},
                metadata={
                    "valid_count": len(valid_flashpoints),
                    "unrelated_count": len(unrelated),
                },
            )

        except Exception as e:
            self.logger.error(
                "FlashpointValidatorAgent failed", error=str(e), exc_info=True
            )
            return AgentResult(success=False, data={}, error=str(e))
