"""Tests for account-related MCP tools."""

import json

from monarch_mcp_server.tools.accounts import (
    get_accounts,
    get_account_holdings,
    refresh_accounts,
    get_account_balance_history,
    upload_account_balance_history,
)


class TestGetAccounts:
    async def test_returns_formatted_account_list(self):
        result = json.loads(await get_accounts())
        assert len(result) == 2
        assert result[0]["id"] == "acc-1"
        assert result[0]["name"] == "Checking Account"
        assert result[0]["type"] == "checking"
        assert result[0]["balance"] == 1500.00
        assert result[0]["institution"] == "Test Bank"
        assert result[0]["is_active"] is True
        assert result[0]["is_hidden"] is False

    async def test_hidden_account_flagged(self):
        result = json.loads(await get_accounts())
        assert result[1]["is_hidden"] is True

    async def test_handles_null_type(self, mock_monarch_client):
        mock_monarch_client.get_accounts.return_value = {
            "accounts": [
                {
                    "id": "acc-3",
                    "displayName": "Unknown",
                    "type": None,
                    "currentBalance": 0,
                    "institution": None,
                    "deactivatedAt": None,
                    "isHidden": False,
                }
            ]
        }
        result = json.loads(await get_accounts())
        assert result[0]["type"] is None
        assert result[0]["institution"] is None

    async def test_handles_empty_accounts(self, mock_monarch_client):
        mock_monarch_client.get_accounts.return_value = {"accounts": []}
        result = json.loads(await get_accounts())
        assert result == []

    async def test_handles_api_error(self, mock_monarch_client):
        mock_monarch_client.get_accounts.side_effect = Exception("API timeout")
        result = await get_accounts()
        assert "get_accounts" in result
        assert "API timeout" in result


class TestGetAccountHoldings:
    async def test_returns_holdings(self):
        result = json.loads(await get_account_holdings("acc-1"))
        assert result["holdings"][0]["name"] == "VTI"
        assert result["holdings"][0]["value"] == 25000.00

    async def test_passes_account_id(self, mock_monarch_client):
        await get_account_holdings("acc-99")
        mock_monarch_client.get_account_holdings.assert_called_once_with("acc-99")

    async def test_handles_api_error(self, mock_monarch_client):
        mock_monarch_client.get_account_holdings.side_effect = Exception("Not found")
        result = await get_account_holdings("bad-id")
        assert "get_account_holdings" in result


class TestRefreshAccounts:
    async def test_refreshes_active_accounts(self, mock_monarch_client):
        result = json.loads(await refresh_accounts())
        assert result["requested"] is True
        assert result["account_count"] == 2
        mock_monarch_client.request_accounts_refresh.assert_called_once_with([
            "acc-1",
            "acc-2",
        ])

    async def test_handles_no_active_accounts(self, mock_monarch_client):
        mock_monarch_client.get_accounts.return_value = {"accounts": []}
        result = json.loads(await refresh_accounts())
        assert result["updated"] is False
        assert result["message"] == "No active accounts found to refresh"
        mock_monarch_client.request_accounts_refresh.assert_not_called()

    async def test_handles_api_error(self, mock_monarch_client):
        mock_monarch_client.request_accounts_refresh.side_effect = Exception("Timeout")
        result = await refresh_accounts()
        assert "refresh_accounts" in result


class TestGetAccountBalanceHistory:
    async def test_returns_formatted_snapshots(self):
        result = json.loads(await get_account_balance_history("12345"))
        assert result["account_id"] == "12345"
        assert result["snapshot_count"] == 3
        assert result["current_balance"] == 1100.0
        assert result["earliest_balance"] == 1000.0
        assert result["highest"] == 1200.0
        assert result["lowest"] == 1000.0
        assert result["snapshots"][0] == {"date": "2026-04-20", "balance": 1000.0}

    async def test_handles_empty_history(self, mock_monarch_client):
        mock_monarch_client.get_account_history.return_value = []
        result = json.loads(await get_account_balance_history("12345"))
        assert result["snapshot_count"] == 0
        assert result["snapshots"] == []

    async def test_handles_api_error(self, mock_monarch_client):
        mock_monarch_client.get_account_history.side_effect = Exception("Not found")
        result = await get_account_balance_history("12345")
        assert "get_account_balance_history" in result


class TestUploadAccountBalanceHistory:
    async def test_applies_corrections(self, mock_monarch_client):
        corrections = json.dumps({"2026-04-21": 900.0})
        result = json.loads(await upload_account_balance_history("12345", corrections))
        assert result["updated"] is True
        assert result["dates_corrected"] == ["2026-04-21"]
        assert result["unmatched_dates"] == []
        assert result["total_snapshots"] == 3

        call_args = mock_monarch_client.upload_account_balance_history.call_args
        assert call_args.kwargs["account_id"] == "12345"
        assert len(call_args.kwargs["csv_content"]) == 3

    async def test_no_matching_dates(self, mock_monarch_client):
        corrections = json.dumps({"2026-01-01": 500.0})
        result = json.loads(await upload_account_balance_history("12345", corrections))
        assert result["updated"] is False
        assert result["unmatched_dates"] == ["2026-01-01"]
        mock_monarch_client.upload_account_balance_history.assert_not_called()

    async def test_surfaces_unmatched_alongside_applied(self, mock_monarch_client):
        corrections = json.dumps({"2026-04-21": 900.0, "2099-12-31": 1.0})
        result = json.loads(await upload_account_balance_history("12345", corrections))
        assert result["updated"] is True
        assert result["dates_corrected"] == ["2026-04-21"]
        assert result["unmatched_dates"] == ["2099-12-31"]

    async def test_dry_run_skips_upload(self, mock_monarch_client):
        corrections = json.dumps({"2026-04-21": 900.0})
        result = json.loads(
            await upload_account_balance_history("12345", corrections, dry_run=True)
        )
        assert result["dry_run"] is True
        assert result["dates_to_correct"] == ["2026-04-21"]
        assert result["total_snapshots"] == 3
        mock_monarch_client.upload_account_balance_history.assert_not_called()

    async def test_rejects_invalid_json(self, mock_monarch_client):
        result = json.loads(
            await upload_account_balance_history("12345", "not json")
        )
        assert result["error"] is True
        assert "valid JSON" in result["message"]
        mock_monarch_client.get_account_history.assert_not_called()

    async def test_rejects_non_object(self, mock_monarch_client):
        result = json.loads(
            await upload_account_balance_history("12345", "[1, 2, 3]")
        )
        assert result["error"] is True
        assert "JSON object" in result["message"]
        mock_monarch_client.get_account_history.assert_not_called()

    async def test_rejects_invalid_date_key(self, mock_monarch_client):
        result = json.loads(
            await upload_account_balance_history("12345", '{"yesterday": 100}')
        )
        assert result["error"] is True
        mock_monarch_client.get_account_history.assert_not_called()

    async def test_rejects_non_numeric_value(self, mock_monarch_client):
        result = json.loads(
            await upload_account_balance_history(
                "12345", '{"2026-04-21": "not-a-number"}'
            )
        )
        assert result["error"] is True
        mock_monarch_client.get_account_history.assert_not_called()

    async def test_handles_api_error(self, mock_monarch_client):
        mock_monarch_client.get_account_history.side_effect = Exception("Timeout")
        result = await upload_account_balance_history("12345", '{"2026-04-21": 0}')
        assert "upload_account_balance_history" in result
