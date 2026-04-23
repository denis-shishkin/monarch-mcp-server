"""Tests for category-related MCP tools."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from monarch_mcp_server.tools.categories import (
    get_categories,
    get_category_groups,
    get_transaction_categories,
    get_transaction_category_groups,
    create_transaction_category,
)


class TestGetCategories:
    """Tests for get_categories tool."""

    @patch('monarch_mcp_server.tools.categories.get_monarch_client')
    async def test_get_categories_success(self, mock_get_client):
        """Test successful retrieval of categories."""
        mock_client = AsyncMock()
        mock_client.get_transaction_categories.return_value = {
            "categories": [
                {
                    "id": "cat_123",
                    "name": "Groceries",
                    "icon": "🛒",
                    "group": {"id": "grp_1", "name": "Food & Dining"},
                    "isSystemCategory": False,
                    "isDisabled": False,
                },
                {
                    "id": "cat_456",
                    "name": "Salary",
                    "icon": "💰",
                    "group": {"id": "grp_2", "name": "Income"},
                    "isSystemCategory": True,
                    "isDisabled": False,
                },
            ]
        }
        mock_get_client.return_value = mock_client

        result = await get_categories()

        categories = json.loads(result)
        assert len(categories) == 2
        assert categories[0]["id"] == "cat_123"
        assert categories[0]["name"] == "Groceries"
        assert categories[0]["group"] == "Food & Dining"
        assert categories[1]["is_system_category"] is True

    @patch('monarch_mcp_server.tools.categories.get_monarch_client')
    async def test_get_categories_empty(self, mock_get_client):
        """Test retrieval when no categories exist."""
        mock_client = AsyncMock()
        mock_client.get_transaction_categories.return_value = {"categories": []}
        mock_get_client.return_value = mock_client

        result = await get_categories()

        categories = json.loads(result)
        assert len(categories) == 0

    @patch('monarch_mcp_server.tools.categories.get_monarch_client')
    async def test_get_categories_error(self, mock_get_client):
        """Test error handling when API fails."""
        mock_get_client.side_effect = RuntimeError("Auth needed")

        result = await get_categories()

        data = json.loads(result)
        assert data["error"] is True
        assert "Auth needed" in data["message"]


class TestGetCategoryGroups:
    """Tests for get_category_groups tool."""

    @patch('monarch_mcp_server.tools.categories.get_monarch_client')
    async def test_get_category_groups_success(self, mock_get_client):
        """Test successful retrieval of category groups."""
        mock_client = AsyncMock()
        mock_client.get_transaction_category_groups.return_value = {
            "categoryGroups": [
                {
                    "id": "grp_1",
                    "name": "Income",
                    "type": "income",
                    "budgetVariability": "fixed",
                    "groupLevelBudgetingEnabled": False,
                    "categories": [
                        {"id": "cat_1", "name": "Salary", "icon": "💰"},
                        {"id": "cat_2", "name": "Bonus", "icon": "🎁"},
                    ],
                },
                {
                    "id": "grp_2",
                    "name": "Food & Dining",
                    "type": "expense",
                    "budgetVariability": "variable",
                    "groupLevelBudgetingEnabled": True,
                    "categories": [
                        {"id": "cat_3", "name": "Groceries", "icon": "🛒"},
                    ],
                },
            ]
        }
        mock_get_client.return_value = mock_client

        result = await get_category_groups()

        groups = json.loads(result)
        assert len(groups) == 2
        assert groups[0]["name"] == "Income"
        assert groups[0]["type"] == "income"
        assert len(groups[0]["categories"]) == 2
        assert groups[1]["group_level_budgeting_enabled"] is True

    @patch('monarch_mcp_server.tools.categories.get_monarch_client')
    async def test_get_category_groups_empty(self, mock_get_client):
        """Test retrieval when no category groups exist."""
        mock_client = AsyncMock()
        mock_client.get_transaction_category_groups.return_value = {"categoryGroups": []}
        mock_get_client.return_value = mock_client

        result = await get_category_groups()

        groups = json.loads(result)
        assert len(groups) == 0

    @patch('monarch_mcp_server.tools.categories.get_monarch_client')
    async def test_get_category_groups_error(self, mock_get_client):
        """Test error handling when API fails."""
        mock_get_client.side_effect = RuntimeError("Connection failed")

        result = await get_category_groups()

        data = json.loads(result)
        assert data["error"] is True
        assert "Connection failed" in data["message"]


class TestGetTransactionCategories:
    async def test_returns_categories(self):
        result = json.loads(await get_transaction_categories())
        assert len(result) == 2
        assert result[0]["id"] == "cat-1"
        assert result[0]["name"] == "Groceries"
        assert result[0]["group"] == "Food"

    async def test_handles_api_error(self, mock_monarch_client):
        mock_monarch_client.get_transaction_categories.side_effect = Exception("boom")
        result = await get_transaction_categories()
        assert "get_transaction_categories" in result


class TestGetTransactionCategoryGroups:
    async def test_returns_groups(self):
        result = json.loads(await get_transaction_category_groups())
        assert len(result) == 2
        assert result[0]["id"] == "grp-1"
        assert result[0]["name"] == "Food"
        assert result[0]["type"] == "expense"

    async def test_handles_api_error(self, mock_monarch_client):
        mock_monarch_client.get_transaction_category_groups.side_effect = Exception("boom")
        result = await get_transaction_category_groups()
        assert "get_transaction_category_groups" in result


class TestCreateTransactionCategory:
    async def test_creates_category(self):
        result = json.loads(await create_transaction_category("grp-1", "Coffee"))
        assert "createCategory" in result

    async def test_passes_required_args(self, mock_monarch_client):
        await create_transaction_category("grp-1", "Coffee")
        mock_monarch_client.create_transaction_category.assert_called_once_with(
            group_id="grp-1", transaction_category_name="Coffee"
        )

    async def test_passes_optional_args(self, mock_monarch_client):
        await create_transaction_category(
            "grp-1", "Coffee", icon="X", rollover_enabled=True, rollover_type="monthly"
        )
        mock_monarch_client.create_transaction_category.assert_called_once_with(
            group_id="grp-1",
            transaction_category_name="Coffee",
            icon="X",
            rollover_enabled=True,
            rollover_type="monthly",
        )

    async def test_handles_api_error(self, mock_monarch_client):
        mock_monarch_client.create_transaction_category.side_effect = Exception("boom")
        result = await create_transaction_category("grp-1", "Coffee")
        assert "create_transaction_category" in result


class TestGetTransactionCategories:
    async def test_returns_categories(self):
        result = json.loads(await get_transaction_categories())
        assert len(result) == 2
        assert result[0]["id"] == "cat-1"
        assert result[0]["name"] == "Groceries"
        assert result[0]["group"] == "Food"

    async def test_handles_api_error(self, mock_monarch_client):
        mock_monarch_client.get_transaction_categories.side_effect = Exception("boom")
        result = await get_transaction_categories()
        assert "get_transaction_categories" in result


class TestGetTransactionCategoryGroups:
    async def test_returns_groups(self):
        result = json.loads(await get_transaction_category_groups())
        assert len(result) == 2
        assert result[0]["id"] == "grp-1"
        assert result[0]["name"] == "Food"
        assert result[0]["type"] == "expense"

    async def test_handles_api_error(self, mock_monarch_client):
        mock_monarch_client.get_transaction_category_groups.side_effect = Exception("boom")
        result = await get_transaction_category_groups()
        assert "get_transaction_category_groups" in result


class TestCreateTransactionCategory:
    async def test_creates_category(self):
        result = json.loads(await create_transaction_category("grp-1", "Coffee"))
        assert "createCategory" in result

    async def test_passes_required_args(self, mock_monarch_client):
        await create_transaction_category("grp-1", "Coffee")
        mock_monarch_client.create_transaction_category.assert_called_once_with(
            group_id="grp-1", transaction_category_name="Coffee"
        )

    async def test_passes_optional_args(self, mock_monarch_client):
        await create_transaction_category(
            "grp-1", "Coffee", icon="X", rollover_enabled=True, rollover_type="monthly"
        )
        mock_monarch_client.create_transaction_category.assert_called_once_with(
            group_id="grp-1",
            transaction_category_name="Coffee",
            icon="X",
            rollover_enabled=True,
            rollover_type="monthly",
        )

    async def test_handles_api_error(self, mock_monarch_client):
        mock_monarch_client.create_transaction_category.side_effect = Exception("boom")
        result = await create_transaction_category("grp-1", "Coffee")
        assert "create_transaction_category" in result
