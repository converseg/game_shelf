from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from game_shelf.suggest.models import SuggestInputs
from game_shelf.suggest.tools import build_suggest_tools


class SuggestAgentResult(BaseModel):
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    note: str = ""


def run_suggest_agent(
    *,
    inputs: SuggestInputs,
    collection_path: str,
    model: str,
    max_bgg_candidates: int,
    no_bgg: bool,
    debug_level: int = 0,
    max_agent_steps: int = 35,
    check_in_every_searches: int = 0,
) -> SuggestAgentResult:
    """
    Runs a LangGraph ReAct agent for `game-shelf suggest`.

    The agent can:
    - call BGG search + thing endpoints repeatedly to build a candidate pool
    - inspect the user's local collection
    - ask the user clarifying questions (interactive)
    - propose a final ranked list of recommendations
    """

    load_dotenv()

    try:
        from langgraph.prebuilt import create_react_agent
    except Exception as e:  # pragma: no cover
        raise RuntimeError("LangGraph is not available. Install dependencies and retry.") from e

    try:
        from langchain_anthropic import ChatAnthropic
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Missing `langchain-anthropic`. Add it to dependencies and run `uv sync`."
        ) from e

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your environment/.env.")

    effective_no_bgg = no_bgg or inputs.mode == "game-night"

    tools = build_suggest_tools(
        collection_path=collection_path,
        max_bgg_candidates=max_bgg_candidates,
        no_bgg=effective_no_bgg,
        verbosity=debug_level,
        check_in_every_searches=check_in_every_searches,
    )

    system_prompt = f"""
You are a board game recommendation assistant.

You MUST use tools to gather evidence before recommending.

Goal:
- Return up to {inputs.count} recommendations that best match the user's constraints and preferences.

Modes:
- game-night: recommend from the user's local collection only (no BGG calls).
- buy: recommend games to buy; you may use BGG search + details; avoid recommending already-owned games.

User inputs (authoritative):
{inputs.model_dump(mode="json")}

Rules:
- Prefer asking 1-2 clarifying questions via `ask_user` if the constraints are ambiguous or too strict.
- For buy mode, run MULTIPLE BGG searches using different queries derived from mechanics/themes/liked games.
- Avoid rate limits: prefer a few high-signal searches (e.g. 3-6) over many small ones.
- Dedupe candidates by source_id, fetch details for likely matches, then filter by constraints.
- If results are weak, iterate: broaden queries and/or ask a clarifying question.
- If a tool returns an item with `type="wrap_up"`, stop searching immediately and produce final recommendations from what you have.
- If a tool returns an item with `type="user_guidance"`, incorporate it and adjust your plan.

Output:
- Respond ONLY as JSON with shape:
  {{ "recommendations": [{{"name": "...", "source": "...", "source_id": "...", "why": "..."}}], "note": "..." }}
""".strip()

    llm = ChatAnthropic(model=model, temperature=0.3, max_tokens=1200)
    agent = create_react_agent(llm, tools, prompt=system_prompt, debug=debug_level >= 2)

    # The ReAct agent expects a messages-style input in most LangGraph setups.
    # We'll pass a single user message containing the task; system prompt is supplied above.
    user_message = "Generate recommendations now. Use tools and follow the rules."
    try:
        result = agent.invoke(
            {"messages": [("user", user_message)]},
            config={"recursion_limit": max_agent_steps},
        )
    except RuntimeError as e:
        return SuggestAgentResult(note=str(e))

    # `result` commonly contains {"messages": [...]} where the last message is the model output.
    messages = result.get("messages", [])
    last = messages[-1] if messages else None
    content = None
    if isinstance(last, tuple) and len(last) == 2:
        content = last[1]
    else:
        content = getattr(last, "content", None)

    if not content:
        return SuggestAgentResult(note="No output from agent.")

    import json

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        # Return raw text as a note to avoid losing the agent output.
        return SuggestAgentResult(note=str(content))

    try:
        return SuggestAgentResult.model_validate(payload)
    except Exception:
        return SuggestAgentResult(note=str(payload))
