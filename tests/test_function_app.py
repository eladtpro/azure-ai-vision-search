import azure.functions as func
from function_app import index

json_event = '''
{
    "id": "c854ff5d-e01e-001f-458c-c8bb35061864",
    "data": {
        "api": "PutBlob",
        "clientRequestId": "06b68280-dab5-4457-b04a-b28b962be03d",
        "requestId": "c854ff5d-e01e-001f-458c-c8bb35000000",
        "eTag": "0x8DC96A3497C852D",
        "contentType": "image/png",
        "contentLength": 405326,
        "blobType": "BlockBlob",
        "url": "https://staiimages.blob.core.windows.net/data/test1.png",
        "sequencer": "0000000000000000000000000001EA0B0000000000363fbf",
        "storageDiagnostics": {"batchId": "ed52cc36-a006-003a-008c-c82386000000"},
    },
    "topic": "/subscriptions/977171a9-6bfd-49c4-a496-018d3312466e/resourceGroups/azure-vision/providers/Microsoft.Storage/storageAccounts/staiimages",
    "subject": "/blobServices/default/containers/data/blobs/test1.png",
    "event_type": "Microsoft.Storage.BlobCreated",
}
'''

event: func.EventGridEvent = func.EventGridEvent(
    subject = json_event["subject"], 
    event_type = json_event["event_type"], 
    data = json_event["data"], 
    data_version = json_event["data"]["eTag"])


result = index(event)

# import azure.functions as func

# EventGridEvent(subject: str, event_type: str, data: object, data_version: str, **kwargs: Any)
# event = func.EventGridEvent()
