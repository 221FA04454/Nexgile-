"""AI orchestrator: authz → intent → retrieve → RAG → provider → validate → audit."""
from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from app.auth.access import assigned_household_ids
from app.core.config import get_settings
from app.models import entities as m
from app.services.audit import record_audit
from app.ai.context import build_authorized_context, mentioned_unauthorized_household
from app.ai.guardrails import DISCLAIMER, is_forbidden_request, refusal_payload, sanitize_answer, unavailable_payload
from app.ai.intents import classify_intent
from app.ai.prompts import compose_system_prompt
from app.ai.providers import resolve_provider
from app.ai.rag.retrieve import retrieve_relevant_documents
from app.ai.rag.store import get_vector_store

log = logging.getLogger("wealthagent.ai")


class AIOrchestrator:
    def __init__(self, db: Session, user: m.User, request_id: str = ""):
        self.db = db
        self.user = user
        self.request_id = request_id
        self.settings = get_settings()

    def chat(self, message: str) -> dict:
        started = time.perf_counter()
        as_of = self.settings.as_of_date
        intent = classify_intent(message)
        allowed = assigned_household_ids(self.db, self.user)
        prompt_text, prompt_name, prompt_version = compose_system_prompt(self.db, intent)

        if is_forbidden_request(message) or intent == "FORBIDDEN_ACTION":
            result = refusal_payload(
                "I cannot execute trades, change beneficiaries, or modify the book of record.",
                as_of,
                prompt_version,
            )
            result.update(self._meta(intent, "deterministic", "guardrail", prompt_version, [], allowed))
            result["prompt_name"] = prompt_name
            self._record(intent, result, duration_ms=(time.perf_counter() - started) * 1000, refused=True)
            return result

        foreign = mentioned_unauthorized_household(self.db, self.user, message)
        if foreign:
            result = refusal_payload(
                f"You are not authorized to access {foreign.name} data.",
                as_of,
                prompt_version,
            )
            result.update(self._meta("CROSS_HOUSEHOLD_PROBE", "deterministic", "authz", prompt_version, [], allowed))
            result["prompt_name"] = prompt_name
            self._record("CROSS_HOUSEHOLD_PROBE", result, duration_ms=(time.perf_counter() - started) * 1000, refused=True)
            return result

        context = build_authorized_context(self.db, self.user, intent)
        context["intent"] = intent
        # RAG is authorization-filtered in SQL before ranking. Never pass other-household chunks.
        documents = [
            d
            for d in retrieve_relevant_documents(self.db, self.user, message)
            if d.get("household_id") in allowed
        ]

        provider = resolve_provider()
        try:
            raw = provider.generate(
                system_prompt=prompt_text,
                user_message=message,
                context=context,
                documents=documents,
            )
        except Exception as exc:
            code = getattr(exc, "code", type(exc).__name__)
            log.error(
                "provider_failed request_id=%s provider=%s code=%s",
                self.request_id,
                provider.name,
                code,
            )
            if self.settings.ai_allow_deterministic_fallback and not self.settings.is_production:
                from app.ai.providers.deterministic import DeterministicProvider

                provider = DeterministicProvider()
                raw = provider.generate(
                    system_prompt=prompt_text,
                    user_message=message,
                    context=context,
                    documents=documents,
                )
            else:
                result = unavailable_payload(as_of, prompt_version, self.request_id)
                result.update(self._meta(intent, "unavailable", "unavailable", prompt_version, [], allowed))
                result["prompt_name"] = prompt_name
                hh = context.get("household") or {}
                result["authorized_household"] = hh.get("name")
                result["authorized_household_id"] = hh.get("id")
                self._record(intent, result, duration_ms=(time.perf_counter() - started) * 1000, refused=False)
                return result

        answer = sanitize_answer(raw.get("answer") or "")
        hh = context.get("household") or {}
        sources = list(raw.get("sources") or [])
        for doc in documents:
            label = f"{doc.get('name')} ({doc.get('category')})"
            if label not in sources:
                sources.append(label)
        result = {
            "reply": answer,
            "answer": answer,
            "sources": sources,
            "as_of": as_of,
            "assumptions": raw.get("assumptions") or [],
            "limitations": raw.get("limitations") or [],
            "advisor_review_required": True,
            "advisor_review_indicator": "Advisor review required before any trade, distribution, or beneficiary change.",
            "disclaimer": raw.get("disclaimer") or DISCLAIMER,
            "engine": provider.name,
            "provider": provider.name,
            "model_version": raw.get("model") or provider.model,
            "prompt_name": prompt_name,
            "prompt_version": prompt_version,
            "intent": intent,
            "authorized_household": hh.get("name"),
            "authorized_household_id": hh.get("id"),
            "role": self.user.role,
            "rag": {
                "backend": get_vector_store().backend_name(),
                "retrieval_count": len(documents),
            },
            "token_usage": raw.get("token_usage") or {},
            "refused": False,
            "conversation_id": f"wa-{self.user.id}-{hh.get('id') or 0}",
        }
        duration = (time.perf_counter() - started) * 1000
        self._record(intent, result, duration_ms=duration, refused=False, documents=documents, provider=provider)
        return result

    def status(self) -> dict:
        provider = resolve_provider()
        groq_ready = bool(self.settings.groq_api_key)
        requested = (self.settings.ai_provider or "deterministic").lower()
        configured = groq_ready if requested == "groq" else True
        return {
            "provider": provider.name,
            "configured": configured,
            "model": getattr(provider, "model", "") or self.settings.groq_model,
            "fallback_available": True,
            "requested_provider": requested,
            "rag_backend": get_vector_store().backend_name(),
            "as_of": self.settings.as_of_date,
            "prompt": "wealth_assistant_v1",
        }

    def sources(self, query: str) -> dict:
        foreign = mentioned_unauthorized_household(self.db, self.user, query)
        if foreign:
            return {"query": query, "results": [], "count": 0, "authorized": False}
        hits = retrieve_relevant_documents(self.db, self.user, query)
        allowed = assigned_household_ids(self.db, self.user)
        safe = [h for h in hits if h.get("household_id") in allowed]
        return {"query": query, "results": safe, "count": len(safe), "authorized": True}

    def _meta(self, intent, provider, model, prompt_version, documents, allowed):
        return {
            "engine": provider,
            "provider": provider,
            "model_version": model,
            "intent": intent,
            "authorized_household": None,
            "authorized_household_id": None,
            "role": self.user.role,
            "prompt_name": "wealth_assistant_v1",
            "rag": {"backend": get_vector_store().backend_name(), "retrieval_count": 0},
            "conversation_id": f"wa-{self.user.id}-0",
        }

    def _record(self, intent, result, duration_ms, refused, documents=None, provider=None):
        documents = documents or []
        hh_id = result.get("authorized_household_id")
        interaction = m.AIInteraction(
            user_id=self.user.id,
            user_email=self.user.email,
            actor_role=self.user.role,
            household_id=hh_id,
            intent=intent,
            provider=(provider.name if provider else result.get("provider") or "deterministic"),
            model=result.get("model_version") or "",
            prompt_name=result.get("prompt_name") or "wealth_assistant_v1",
            prompt_version=result.get("prompt_version") or "",
            data_scope={"household_id": hh_id, "allowed": sorted(assigned_household_ids(self.db, self.user))},
            document_source_ids=[d.get("document_id") for d in documents],
            response_status="refused" if refused else "success",
            request_id=self.request_id,
            duration_ms=round(duration_ms, 2),
            retrieval_count=len(documents),
            source_count=len(result.get("sources") or []),
            token_usage=result.get("token_usage") or {},
            refused=refused,
        )
        self.db.add(interaction)
        record_audit(
            self.db,
            actor=self.user.email,
            actor_role=self.user.role,
            action="ai_chat",
            entity_type="AI",
            entity_id=str(hh_id or ""),
            after={
                "intent": intent,
                "provider": interaction.provider,
                "prompt_version": interaction.prompt_version,
                "refused": refused,
                "retrieval_count": interaction.retrieval_count,
            },
            request_id=self.request_id,
        )
        log.info(
            "ai_complete intent=%s provider=%s duration_ms=%.0f retrieval=%s refused=%s",
            intent,
            interaction.provider,
            duration_ms,
            interaction.retrieval_count,
            refused,
        )
