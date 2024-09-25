# List all resource groups
resource_groups=$(az group list --query "[].name" -o tsv)

# Iterate through each resource group
for rg in $resource_groups; do
  # List all virtual networks in the resource group
  vnets=$(az network vnet list --resource-group $rg --query "[].name" -o tsv)
  
  # Iterate through each virtual network
  for vnet in $vnets; do
    # List all peerings for the virtual network
    # echo "Peerings for VNet: $vnet in Resource Group: $rg"
    az network vnet peering list --resource-group $rg --vnet-name $vnet --output table
  done
done
