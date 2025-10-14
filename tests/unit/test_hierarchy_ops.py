"""
Unit tests for hierarchy operations.

Tests the hierarchy building functionality including:
- Level parsing
- Parent finding
- Hierarchy validation
- Multi-level hierarchies (up to 15 levels)
"""

import pytest
from operations.hierarchy_ops import (
    parse_level,
    find_parent_article,
    build_hierarchy,
    validate_hierarchy,
    get_hierarchy_summary,
)
from domain.exceptions import ImportValidationError, ValidationError


class TestParseLevel:
    """Test level string parsing."""

    def test_single_level(self):
        """Test parsing single level."""
        depth, path = parse_level("1")
        assert depth == 1
        assert path == [1]

    def test_two_levels(self):
        """Test parsing two levels."""
        depth, path = parse_level("1.2")
        assert depth == 2
        assert path == [1, 2]

    def test_three_levels(self):
        """Test parsing three levels."""
        depth, path = parse_level("1.2.3")
        assert depth == 3
        assert path == [1, 2, 3]

    def test_deep_hierarchy_15_levels(self):
        """Test parsing maximum 15 levels."""
        level_str = ".".join(str(i) for i in range(1, 16))  # 1.2.3...15
        depth, path = parse_level(level_str)
        assert depth == 15
        assert path == list(range(1, 16))

    def test_too_deep_hierarchy(self):
        """Test that >15 levels raises error."""
        level_str = ".".join(str(i) for i in range(1, 17))  # 1.2.3...16
        with pytest.raises(ValidationError) as exc_info:
            parse_level(level_str)
        assert "för djup" in str(exc_info.value).lower()

    def test_empty_level(self):
        """Test that empty level raises error."""
        with pytest.raises(ValidationError):
            parse_level("")

    def test_invalid_format_letters(self):
        """Test that non-numeric levels raise error."""
        with pytest.raises(ValidationError):
            parse_level("1.a.3")

    def test_invalid_format_negative(self):
        """Test that negative numbers raise error."""
        with pytest.raises(ValidationError):
            parse_level("1.-2.3")

    def test_level_with_zero(self):
        """Test that zero is allowed (for special/spare parts)."""
        depth, path = parse_level("0")
        assert depth == 1
        assert path == [0]

        # Zero can appear in paths too
        depth, path = parse_level("1.0.3")
        assert depth == 3
        assert path == [1, 0, 3]


class TestFindParentArticle:
    """Test finding parent articles in hierarchy."""

    def test_top_level_no_parent(self):
        """Test that level 1 has no parent."""
        stack = []
        parent = find_parent_article([1], stack)
        assert parent is None

    def test_level_2_finds_level_1_parent(self):
        """Test that level 2 finds level 1 as parent."""
        stack = [
            {"article_number": "MOTOR-001", "level": "1"},
        ]
        parent = find_parent_article([1, 1], stack)
        assert parent == "MOTOR-001"

    def test_level_3_finds_level_2_parent(self):
        """Test that level 3 finds level 2 as parent."""
        stack = [
            {"article_number": "MOTOR-001", "level": "1"},
            {"article_number": "1.1", "level": "1.1"},
        ]
        parent = find_parent_article([1, 1, 1], stack)
        assert parent == "1.1"

    def test_deep_hierarchy_5_levels(self):
        """Test finding parent in 5-level hierarchy."""
        stack = [
            {"article_number": "L1", "level": "1"},
            {"article_number": "L2", "level": "1.1"},
            {"article_number": "L3", "level": "1.1.1"},
            {"article_number": "L4", "level": "1.1.1.1"},
        ]
        parent = find_parent_article([1, 1, 1, 1, 1], stack)
        assert parent == "L4"


class TestValidateHierarchy:
    """Test hierarchy validation."""

    def test_valid_simple_hierarchy(self):
        """Test that valid simple hierarchy passes."""
        articles = [
            {"article_number": "A", "level": "1"},
            {"article_number": "B", "level": "2"},
        ]
        # Should not raise
        validate_hierarchy(articles)

    def test_valid_multi_level(self):
        """Test that valid multi-level hierarchy passes."""
        articles = [
            {"article_number": "A", "level": "1"},
            {"article_number": "B", "level": "1.1"},
            {"article_number": "C", "level": "1.1.1"},
            {"article_number": "D", "level": "1.2"},
        ]
        # Should not raise
        validate_hierarchy(articles)

    def test_missing_level_field(self):
        """Test that missing level field raises error."""
        articles = [
            {"article_number": "A"},  # Missing level
        ]
        with pytest.raises(ImportValidationError) as exc_info:
            validate_hierarchy(articles)
        assert "level" in str(exc_info.value).lower()

    def test_empty_level(self):
        """Test that empty level raises error."""
        articles = [
            {"article_number": "A", "level": ""},
        ]
        with pytest.raises(ImportValidationError):
            validate_hierarchy(articles)

    def test_skipped_level(self):
        """Test that skipped levels raise error."""
        articles = [
            {"article_number": "A", "level": "1"},
            {"article_number": "B", "level": "1.1.1"},  # Skipped level 1.1 (depth jump from 1 to 3)
        ]
        with pytest.raises(ImportValidationError) as exc_info:
            validate_hierarchy(articles)
        assert "hoppad" in str(exc_info.value).lower()

    def test_empty_articles_list(self):
        """Test that empty list is valid."""
        validate_hierarchy([])  # Should not raise


class TestBuildHierarchy:
    """Test complete hierarchy building."""

    def test_simple_two_level_hierarchy(self):
        """Test building simple 2-level hierarchy."""
        articles = [
            {"article_number": "MOTOR-001", "level": "1", "sort_order": 0},
            {"article_number": "1.1", "level": "1.1", "sort_order": 1},  # level is "1.1", not "2"
        ]

        result = build_hierarchy(articles)

        assert len(result) == 2
        assert result[0]["parent_article"] is None
        assert result[0]["level_depth"] == 1
        assert result[1]["parent_article"] == "MOTOR-001"
        assert result[1]["level_depth"] == 2

    def test_three_level_hierarchy(self):
        """Test building 3-level hierarchy."""
        articles = [
            {"article_number": "A", "level": "1", "sort_order": 0},
            {"article_number": "B", "level": "1.1", "sort_order": 1},
            {"article_number": "C", "level": "1.1.1", "sort_order": 2},
        ]

        result = build_hierarchy(articles)

        assert result[0]["parent_article"] is None
        assert result[1]["parent_article"] == "A"
        assert result[2]["parent_article"] == "B"

    def test_multiple_children_same_level(self):
        """Test multiple children at same level."""
        articles = [
            {"article_number": "MOTOR", "level": "1", "sort_order": 0},
            {"article_number": "1.1", "level": "1.1", "sort_order": 1},
            {"article_number": "1.2", "level": "1.2", "sort_order": 2},
            {"article_number": "1.3", "level": "1.3", "sort_order": 3},
        ]

        result = build_hierarchy(articles)

        assert result[0]["parent_article"] is None
        assert result[1]["parent_article"] == "MOTOR"
        assert result[2]["parent_article"] == "MOTOR"
        assert result[3]["parent_article"] == "MOTOR"

    def test_branching_hierarchy(self):
        """Test branching hierarchy with sub-branches."""
        articles = [
            {"article_number": "MOTOR", "level": "1", "sort_order": 0},
            {"article_number": "1.1", "level": "1.1", "sort_order": 1},
            {"article_number": "1.1.1", "level": "1.1.1", "sort_order": 2},
            {"article_number": "1.1.2", "level": "1.1.2", "sort_order": 3},
            {"article_number": "1.2", "level": "1.2", "sort_order": 4},
            {"article_number": "1.2.1", "level": "1.2.1", "sort_order": 5},
        ]

        result = build_hierarchy(articles)

        assert result[0]["parent_article"] is None  # MOTOR
        assert result[1]["parent_article"] == "MOTOR"  # 1.1
        assert result[2]["parent_article"] == "1.1"  # 1.1.1
        assert result[3]["parent_article"] == "1.1"  # 1.1.2
        assert result[4]["parent_article"] == "MOTOR"  # 1.2
        assert result[5]["parent_article"] == "1.2"  # 1.2.1

    def test_deep_15_level_hierarchy(self):
        """Test maximum 15-level hierarchy."""
        articles = []
        for i in range(1, 16):
            level_str = ".".join(str(j) for j in range(1, i + 1))
            articles.append({
                "article_number": f"L{i}",
                "level": level_str,
                "sort_order": i - 1
            })

        result = build_hierarchy(articles)

        assert len(result) == 15
        assert result[0]["parent_article"] is None  # Level 1
        assert result[1]["parent_article"] == "L1"  # Level 2
        assert result[14]["parent_article"] == "L14"  # Level 15

    def test_preserves_sort_order(self):
        """Test that sort_order is preserved."""
        articles = [
            {"article_number": "A", "level": "1", "sort_order": 5},
            {"article_number": "B", "level": "2", "sort_order": 10},
        ]

        result = build_hierarchy(articles)

        assert result[0]["sort_order"] == 5
        assert result[1]["sort_order"] == 10

    def test_adds_sort_order_if_missing(self):
        """Test that sort_order is added if missing."""
        articles = [
            {"article_number": "A", "level": "1"},  # No sort_order
            {"article_number": "B", "level": "2"},
        ]

        result = build_hierarchy(articles)

        assert result[0]["sort_order"] == 0  # Added automatically
        assert result[1]["sort_order"] == 1

    def test_returns_back_to_lower_level(self):
        """Test hierarchy that returns to lower level after deep nesting."""
        articles = [
            {"article_number": "A", "level": "1", "sort_order": 0},
            {"article_number": "B", "level": "1.1", "sort_order": 1},
            {"article_number": "C", "level": "1.1.1", "sort_order": 2},
            {"article_number": "D", "level": "1.2", "sort_order": 3},  # Back to level 2
        ]

        result = build_hierarchy(articles)

        assert result[0]["parent_article"] is None
        assert result[1]["parent_article"] == "A"
        assert result[2]["parent_article"] == "B"
        assert result[3]["parent_article"] == "A"  # Parent is A, not C


class TestGetHierarchySummary:
    """Test hierarchy summary statistics."""

    def test_summary_empty_list(self):
        """Test summary for empty articles list."""
        summary = get_hierarchy_summary([])

        assert summary["total_articles"] == 0
        assert summary["max_depth"] == 0
        assert summary["top_level_count"] == 0

    def test_summary_simple_hierarchy(self):
        """Test summary for simple hierarchy."""
        articles = [
            {"article_number": "A", "level_depth": 1},
            {"article_number": "B", "level_depth": 2},
            {"article_number": "C", "level_depth": 2},
        ]

        summary = get_hierarchy_summary(articles)

        assert summary["total_articles"] == 3
        assert summary["max_depth"] == 2
        assert summary["top_level_count"] == 1
        assert summary["by_depth"][1] == 1
        assert summary["by_depth"][2] == 2

    def test_summary_deep_hierarchy(self):
        """Test summary for deep hierarchy."""
        articles = [
            {"article_number": "A", "level_depth": 1},
            {"article_number": "B", "level_depth": 2},
            {"article_number": "C", "level_depth": 3},
            {"article_number": "D", "level_depth": 4},
            {"article_number": "E", "level_depth": 5},
        ]

        summary = get_hierarchy_summary(articles)

        assert summary["total_articles"] == 5
        assert summary["max_depth"] == 5
        assert summary["top_level_count"] == 1
        assert all(summary["by_depth"][i] == 1 for i in range(1, 6))


class TestIntegration:
    """Integration tests for complete workflow."""

    def test_complete_workflow_with_real_data(self):
        """Test complete workflow with realistic data."""
        # Simulate nivålista import
        raw_articles = [
            {
                "article_number": "MOTOR-12345",
                "description": "Huvudmotor",
                "quantity": 1.0,
                "level": "1",
            },
            {
                "article_number": "STATOR-001",
                "description": "Stator",
                "quantity": 1.0,
                "level": "1.1",
            },
            {
                "article_number": "ROTOR-001",
                "description": "Rotor",
                "quantity": 1.0,
                "level": "1.2",
            },
            {
                "article_number": "AXEL-001",
                "description": "Axel",
                "quantity": 1.0,
                "level": "1.2.1",
            },
            {
                "article_number": "LAGER-001",
                "description": "Lager",
                "quantity": 2.0,
                "level": "1.2.2",
            },
            {
                "article_number": "KAPA-001",
                "description": "Kåpa",
                "quantity": 1.0,
                "level": "1.3",
            },
        ]

        # Build hierarchy
        result = build_hierarchy(raw_articles)

        # Verify structure
        assert len(result) == 6

        # Check MOTOR (top-level)
        motor = result[0]
        assert motor["article_number"] == "MOTOR-12345"
        assert motor["parent_article"] is None
        assert motor["level_depth"] == 1

        # Check STATOR (child of MOTOR)
        stator = result[1]
        assert stator["article_number"] == "STATOR-001"
        assert stator["parent_article"] == "MOTOR-12345"
        assert stator["level_depth"] == 2

        # Check ROTOR (child of MOTOR)
        rotor = result[2]
        assert rotor["article_number"] == "ROTOR-001"
        assert rotor["parent_article"] == "MOTOR-12345"
        assert rotor["level_depth"] == 2

        # Check AXEL (child of ROTOR)
        axel = result[3]
        assert axel["article_number"] == "AXEL-001"
        assert axel["parent_article"] == "ROTOR-001"
        assert axel["level_depth"] == 3

        # Check LAGER (child of ROTOR)
        lager = result[4]
        assert lager["article_number"] == "LAGER-001"
        assert lager["parent_article"] == "ROTOR-001"
        assert lager["level_depth"] == 3

        # Check KAPA (child of MOTOR)
        kapa = result[5]
        assert kapa["article_number"] == "KAPA-001"
        assert kapa["parent_article"] == "MOTOR-12345"
        assert kapa["level_depth"] == 2

        # Verify summary
        summary = get_hierarchy_summary(result)
        assert summary["total_articles"] == 6
        assert summary["max_depth"] == 3
        assert summary["top_level_count"] == 1
        assert summary["by_depth"][1] == 1  # 1 top-level
        assert summary["by_depth"][2] == 3  # 3 at level 2
        assert summary["by_depth"][3] == 2  # 2 at level 3
