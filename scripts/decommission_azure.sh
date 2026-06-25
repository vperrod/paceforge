#!/usr/bin/env bash
# Decommission the old Azure hosting — this is what stops the monthly bill.
# DESTRUCTIVE. Run ONLY after you've verified the file-based flow works
# (paceforge sync / push) and migrated your data (scripts/migrate_from_sqlite.py).
#
# Requires: az login. Set PACEFORGE_RG to the resource group. Pass --yes to skip prompt.
set -euo pipefail

RG="${PACEFORGE_RG:-}"
if [ -z "$RG" ]; then
  echo "Set PACEFORGE_RG to the resource group containing the PaceForge resources." >&2
  exit 1
fi

echo "Resource group: $RG"
echo "Will DELETE:"
echo "  - App Service: paceforge-dev"
echo "  - App Service: paceforge-app"
echo "  - Container Registry: paceforgeacr"

if [ "${1:-}" != "--yes" ]; then
  read -r -p "Type 'delete' to proceed: " confirm
  [ "$confirm" = "delete" ] || { echo "Aborted."; exit 1; }
fi

az webapp delete --resource-group "$RG" --name paceforge-dev  || echo "paceforge-dev: not found / already gone"
az webapp delete --resource-group "$RG" --name paceforge-app  || echo "paceforge-app: not found / already gone"
az acr  delete  --resource-group "$RG" --name paceforgeacr --yes || echo "paceforgeacr: not found / already gone"

echo "Done. Check the Azure portal Cost Management to confirm nothing is still billing."
