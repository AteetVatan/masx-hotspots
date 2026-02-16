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
Domain Classifier Agent for MASX-HOTSPOTS Agentic AI System.

Identifies geopolitical domains from content using LLM classification.
Supports 12 high-level categories including geopolitical, military, economic, etc.

Usage:
    from app.agents.domain_classifier import DomainClassifier

    classifier = DomainClassifier()
    result = classifier.run({"title": "...", "description": "..."})
"""

from typing import Any, Dict, List

from .base import BaseAgent, AgentResult
from ..services.llm_service import LLMService
from ..core.exceptions import AgentException
from ..constants import DOMAIN_CATEGORIES


class DomainClassifier(BaseAgent):
    """
    Agent for classifying content into geopolitical domains.

    Identifies which of 12 high-level categories content falls under:
    - Geopolitical, Military/Conflict, Economic/Trade, Cultural/Identity
    - Religious/Ideological, Technological, Cybersecurity, Environmental
    - Civilizational/Ethnonationalist, AI Governance, Migration, Sovereignty
    """

    def __init__(self):
        """Initialize the Domain Classifier agent."""
        super().__init__(
            name="DomainClassifier",
            description="Classifies content into geopolitical domains using LLM analysis",
        )
        self.llm_service = LLMService.get_instance()  # singleton
        self.domain_categories = DOMAIN_CATEGORIES

    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute domain classification.
        Args: input_data: Dictionary containing 'title' and 'description' fields
        Returns: AgentResult: Classification result with identified domains
        """
        try:
            # Validate input
            if not self.validate_input(input_data):
                raise AgentException("Invalid input: missing title or description")

            # Extract content
            title = input_data.get("title", "")
            description = input_data.get("description", "")

            # Generate classification prompt
            prompt = self._build_classification_prompt(title, description)

            # Get LLM response
            response = self.llm_service.generate_text(
                prompt,
                system_prompt="You are a geopolitical taxonomy expert.",
                temperature=0.0,  # Deterministic classification
            )

            # Parse domains from response
            domains = self._parse_domains(response)

            # Validate domains do we need this? as llm can provide us with extra domains
            # or should we stick to the domains defined by us?
            validated_domains = self._validate_domains(domains)

            return AgentResult(
                success=True,
                data={
                    "domains": validated_domains,
                    "confidence": self._calculate_confidence(validated_domains),
                    "raw_response": response,
                },
                metadata={
                    "input_length": len(title) + len(description),
                    "domain_count": len(validated_domains),
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Domain classification failed: {str(e)}",
                metadata={"exception_type": type(e).__name__},
            )

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for domain classification.
        Args: input_data: Input data to validate
        Returns: bool: True if input is valid
        """
        if not isinstance(input_data, dict):
            return False

        # Must have at least title or description
        title = input_data.get("title", "")
        description = input_data.get("description", "")
        return bool(title.strip() or description.strip())

    def _build_classification_prompt(self, title: str, description: str) -> str:
        """Build the classification prompt for the LLM.
        Args:title: Content title
             description: Content description
        Returns:str: Formatted prompt for domain classification
        """
        categories_text = "\n".join(
            f"- {category}" for category in self.domain_categories
        )

        return f"""
        Given the following content, identify which of the following high-level geopolitical categories it falls under. 
        Return a comma-separated list of relevant categories.
        Categories: {categories_text}
        Content:
        Title: {title}
        Description: {description}

        Respond with comma-separated categories only. If no clear category applies, return "Uncategorized".
        """

    def _parse_domains(self, response: str) -> List[str]:
        """
        Parse domain categories from LLM response.
        Args: response: Raw LLM response
        Returns: List[str]: List of identified domains
        """
        # Clean response
        cleaned = response.strip().lower()

        # Handle "Uncategorized" case
        if "uncategorized" in cleaned:
            return ["Uncategorized"]

        # Split by comma and clean each domain
        domains = []
        for domain in cleaned.split(","):
            domain = domain.strip()
            if domain:
                # Map back to original case
                for original in self.domain_categories:
                    if domain in original.lower():
                        domains.append(original)
                        break
                else:
                    # If no exact match, add as-is (for edge cases)
                    domains.append(domain.title())

        return domains

    def _validate_domains(self, domains: List[str]) -> List[str]:
        """
        Validate and filter domains against known categories.

        Args: domains: List of identified domains
        Returns: List[str]: Validated domains
        """
        valid_domains = []
        for domain in domains:
            if domain in self.domain_categories or domain == "Uncategorized":
                valid_domains.append(domain)
            else:
                self.logger.warning(f"Unknown domain category: {domain}")

        return valid_domains

    def _calculate_confidence(self, domains: List[str]) -> float:
        """
        Calculate confidence score for the classification.
        Args: domains: List of identified domains
        Returns: float: Confidence score (0.0 to 1.0)
        """
        if not domains:
            return 0.0

        # Simple confidence based on number of domains
        # Fewer domains = higher confidence (more specific)
        if len(domains) == 1:
            return 0.9
        elif len(domains) == 2:
            return 0.7
        elif len(domains) == 3:
            return 0.5
        else:
            return 0.3

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities and metadata."""
        capabilities = super().get_capabilities()
        capabilities.update(
            {
                "domains": self.domain_categories,
                "max_domains": len(self.domain_categories),
                "supports_uncategorized": True,
            }
        )
        return capabilities
