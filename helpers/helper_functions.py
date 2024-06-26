import datetime
import os  
import requests  
import logging  
from azure.storage.blob import BlobClient, generate_blob_sas, BlobSasPermissions

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