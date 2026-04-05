"""Tests for SkillRegistry."""

from __future__ import annotations

import pytest

from openclaw_skills.registry import SkillRegistry
from openclaw_skills.skills.base import BaseSkill
from tests.conftest import HaltingSkill, PassthroughSkill


class TestSkillRegistry:
    def test_register_and_list(self) -> None:
        registry = SkillRegistry()
        registry.register("passthrough", PassthroughSkill)

        available = registry.list_available()
        # Includes built-in skills + newly registered
        assert any(s["name"] == "passthrough" for s in available)

    def test_register_duplicate_raises(self) -> None:
        registry = SkillRegistry()
        registry.register("passthrough", PassthroughSkill)
        with pytest.raises(ValueError, match="already registered"):
            registry.register("passthrough", PassthroughSkill)

    @pytest.mark.asyncio
    async def test_get_instantiates(self) -> None:
        registry = SkillRegistry()
        registry.register("passthrough", PassthroughSkill)

        skill = await registry.get("passthrough")
        assert isinstance(skill, PassthroughSkill)
        assert skill.name == "passthrough"

    @pytest.mark.asyncio
    async def test_get_caches_instance(self) -> None:
        registry = SkillRegistry()
        registry.register("passthrough", PassthroughSkill)

        skill1 = await registry.get("passthrough")
        skill2 = await registry.get("passthrough")
        assert skill1 is skill2

    @pytest.mark.asyncio
    async def test_get_unknown_raises(self) -> None:
        registry = SkillRegistry()
        with pytest.raises(KeyError, match="Unknown skill"):
            await registry.get("nonexistent")

    @pytest.mark.asyncio
    async def test_shutdown_all(self) -> None:
        registry = SkillRegistry()
        registry.register("passthrough", PassthroughSkill)
        await registry.get("passthrough")

        await registry.shutdown_all()
        # After shutdown, instances are cleared
        assert "passthrough" not in registry._instances

    def test_is_registered(self) -> None:
        registry = SkillRegistry()
        assert not registry.is_registered("test")
        registry.register("test", PassthroughSkill)
        assert registry.is_registered("test")

    def test_registered_names(self) -> None:
        registry = SkillRegistry()
        registry.register("b_skill", PassthroughSkill)
        registry.register("a_skill", HaltingSkill)
        names = registry.registered_names
        assert "a_skill" in names
        assert "b_skill" in names
        # Also includes built-in skills
        assert "state_tracker" in names
