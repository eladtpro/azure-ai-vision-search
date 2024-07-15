import datetime
import os
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import requests
import logging
from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobServiceClient,
    # ContainerClient,
    BlobClient,
    BlobSasPermissions,
    # ContainerSasPermissions,
    UserDelegationKey,
    # generate_container_sas,
    generate_blob_sas
)


def get_image_embeddings(imageUrl, sas_token):  
    cogSvcsEndpoint = os.environ["AI_VISION_ENDPOINT"]  
    cogSvcsApiKey = os.environ["AI_VISION_API_KEY"]  
 
    url = f"{cogSvcsEndpoint}/computervision/retrieval:vectorizeImage"  
 
    params = {  
        "api-version": "2023-02-01-preview"  
    }  
 
    headers = {  
        "Content-Type": "application/json",  
        "Ocp-Apim-Subscription-Key": cogSvcsApiKey  
    }  
 
    data = {  
        "url": f"{imageUrl}?{sas_token}"
    }  
    
 
    response = requests.post(url, params=params, headers=headers, json=data)  
 
    if response.status_code != 200:  
        logging.error(f"Error: {response.status_code}, {response.text}")  
        response.raise_for_status()  
 
    embeddings = response.json()["vector"]  
    return embeddings  


# =========   BEGIN: USER DELEGATED SAS TOKEN =========

# https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme?view=azure-python#service-principal-with-secret
# https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-user-delegation-sas-create-python

# ADD THIS TO THE ENVIRONMENT VARIABLES:
# AZURE_CLIENT_ID	    ID of a Microsoft Entra application
# AZURE_TENANT_ID	    ID of the application's Microsoft Entra tenant
# AZURE_CLIENT_SECRET	one of the application's client secrets

def create_user_delegated_sas_token(imageUrl, auth_header):
    # Construct the blob endpoint from the account name
    # account_url = "https://<storage-account-name>.blob.core.windows.net"
    parsed_url = urlparse(imageUrl)
    account_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    #Create a BlobServiceClient object using DefaultAzureCredential
    # TODO: optimize service client to fetch all images in one go
    # blob_service_client = BlobServiceClient(account_url, credential=DefaultAzureCredential())
    user_delegation_key = get_user_delegated_key(account_url, auth_header)
    # user_delegation_key = request_user_delegation_key(blob_service_client)
    blob_client = BlobClient.from_blob_url(imageUrl, credential=user_delegation_key)
    sas_token = create_user_delegation_sas_token(blob_client, user_delegation_key)
    return sas_token


# https://learn.microsoft.com/en-us/rest/api/storageservices/get-user-delegation-key
def get_user_delegated_key(account_url, auth_header):
    postfix = "?restype=service&comp=userdelegationkey"
    url = account_url + postfix
    delegation_key_start_time = datetime.datetime.now(datetime.timezone.utc)
    delegation_key_expiry_time = delegation_key_start_time + datetime.timedelta(days=1)

    start_time_str = delegation_key_start_time.isoformat() + "Z"
    expiry_time_str = delegation_key_expiry_time.isoformat() + "Z"

    # XML body
    xml_body = f"""
    <key-info>
      <start>{start_time_str}</start>
      <expiry>{expiry_time_str}</expiry>
    </key-info>
    """
    logging.info(f"XML body: {xml_body}")
    headers = {
        "Authorization": auth_header,
        "x-ms-version": "2024-08-04",
        "Content-Type": "application/xml"
    }

    response = requests.post(url, headers=headers, data=xml_body)

    if response.status_code == 200:
        # Parse the XML response
        root = ET.fromstring(response.content)
        user_delegation_key = {
            "SignedOid": root.findtext("SignedOid"),
            "SignedTid": root.findtext("SignedTid"),
            "SignedStart": root.findtext("SignedStart"),
            "SignedExpiry": root.findtext("SignedExpiry"),
            "SignedService": root.findtext("SignedService"),
            "SignedVersion": root.findtext("SignedVersion"),
            "Value": root.findtext("Value")
        }
        return user_delegation_key
    else:
        response.raise_for_status()
def request_user_delegation_key(blob_service_client: BlobServiceClient) -> UserDelegationKey:
    # Get a user delegation key that's valid for 1 day
    delegation_key_start_time = datetime.datetime.now(datetime.timezone.utc)
    delegation_key_expiry_time = delegation_key_start_time + datetime.timedelta(days=1)

    user_delegation_key = blob_service_client.get_user_delegation_key(
        key_start_time=delegation_key_start_time,
        key_expiry_time=delegation_key_expiry_time
    )

    return user_delegation_key


def create_user_delegation_sas_token(blob_client: BlobClient, user_delegation_key: UserDelegationKey):
    # Create a SAS token that's valid for one day, as an example
    start_time = datetime.datetime.now(datetime.timezone.utc)
    expiry_time = start_time + datetime.timedelta(days=1)

    sas_token = generate_blob_sas(
        account_name=blob_client.account_name,
        container_name=blob_client.container_name,
        blob_name=blob_client.blob_name,
        user_delegation_key=user_delegation_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry_time,
        start=start_time
    )

    return sas_token

# =========   END: USER DELEGATED SAS TOKEN =========


def create_service_sas_blob(imageUrl):
    #Env variables:
    account_key = os.environ["ACCOUNT_KEY"]
    
    blob_client = BlobClient.from_blob_url(
        blob_url=imageUrl,
        credential=account_key
    )
    
    # Create a SAS token that's valid for one hour, as an example
    start_time = datetime.datetime.now(datetime.timezone.utc)
    expiry_time = start_time + datetime.timedelta(hours=1)

    sas_token = generate_blob_sas(
        account_name= blob_client.account_name,
        container_name= blob_client.container_name,
        blob_name= blob_client.blob_name,
        account_key= account_key,
        permission= BlobSasPermissions(read=True),
        expiry= expiry_time,
        start= start_time
    )
    
    return sas_token