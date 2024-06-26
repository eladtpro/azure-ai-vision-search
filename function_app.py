import os
import random
import azure.functions as func
import logging
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
import requests
import json
import time
from azure.search.documents.models import VectorizedQuery
from helpers import helper_functions


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
search_client: SearchClient = None
chat_client: AzureOpenAI = None

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPEN_AI_MODEL = os.getenv("OPEN_AI_MODEL")
API_VERSION = os.getenv("API_VERSION")
AI_VISION_ENDPOINT = os.getenv("AI_VISION_ENDPOINT")
AI_VISION_API_KEY = os.getenv("AI_VISION_API_KEY")
AI_SEARCH_SERVICE_ENDPOINT = os.getenv("AI_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
AI_SEARCH_INDEX_NAME = os.getenv("AI_SEARCH_INDEX_NAME")

logging.info(f"AOAI endpoint ==> {AZURE_OPENAI_ENDPOINT}")
logging.info(f"AI_VISION_ENDPOINT endpoint ==> {AI_VISION_ENDPOINT}")

@app.function_name(name="url")
@app.route(route="url", methods=["GET"])
def url(req: func.HttpRequest) -> func.HttpResponse:
    vision_url = f"{AI_VISION_ENDPOINT}/computervision/models?api-version=2023-02-01-preview"
    logging.info(f"url HttpRequest triggered: {vision_url}")
    return f"{vision_url}"


@app.function_name(name="test")
@app.route(route="test", methods=["GET"])
def test(req: func.HttpRequest) -> func.HttpResponse:
    vision_url = f"{AI_VISION_ENDPOINT}/computervision/models?api-version=2023-02-01-preview"
    logging.info(f"test HttpRequest triggered: {vision_url}")
    headers = {"Ocp-Apim-Subscription-Key": AI_VISION_API_KEY}

    response = requests.get(vision_url, headers=headers)
    if response.status_code == 200:
        return response.json()

    return func.HttpResponse(f"ERROR: {response.status_code} - {response.text}",
                             status_code=response.status_code, mimetype="text/plain")


@app.function_name(name="index")
@app.event_grid_trigger(arg_name="event")
def index(event: func.EventGridEvent):
    result = json.dumps({
        'id': event.id,
        'data': event.get_json(),
        'topic': event.topic,
        'subject': event.subject,
        'event_type': event.event_type,
    })
    logging.info('index EventGrid trigger processed an event: %s', result)

    event_json = event.get_json()  # This gives you the event data as a dictionary.
    
    # Access 'clientRequestId' and 'url' directly from the event's JSON.
    client_request_id = event_json["clientRequestId"]
    image_url = event_json["url"]
    
    # Construct the desired JSON structure with the extracted values.
    event_data = {
        "recordId": client_request_id,
        "data": {
            "imageUrl": image_url
        }
    }
    
    logging.info(f"EventGrid trigger processed an event: {event_data}")    

    values = [event_data]
    response_values = vectorizeImage(values)

    # Create the response object
    response_body = {"IndexRaw values": response_values}
    logging.info(f"IndexRaw Response body: {response_body}")

    global search_client
    if search_client is None:
        logging.info(f"Creating search client. AI_SEARCH_SERVICE_ENDPOINT: {AI_SEARCH_SERVICE_ENDPOINT}, AI_SEARCH_INDEX_NAME: {AI_SEARCH_INDEX_NAME}, AZURE_SEARCH_ADMIN_KEY: {AZURE_SEARCH_ADMIN_KEY}")
        search_client = SearchClient(
            AI_SEARCH_SERVICE_ENDPOINT,
            AI_SEARCH_INDEX_NAME,
            AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY),
        )

    # [START upload_document]
    doc = {
        "id": image_url,
        "imageUrl": image_url,
        "imageVector": json.dumps(response_values),
        "title": "Azure Inn",
    }

    result = search_client.upload_documents(documents=[doc])
    logging.info(f"Upload documents result: {result}")


@app.route(route="indexraw", methods=["GET"])
def indexraw(req: func.HttpRequest) -> func.HttpResponse:
    image_url = req.params.get('url')
    recordId = req.params.get('id') or random.randint(1, 1000)
    event_data = {
        "recordId": recordId,
        "data": {
            "imageUrl": image_url
        }
    }
    
    logging.info(f"HttpRequest trigger processed an event: {event_data}")
    values = [event_data]
    response_values = vectorizeImage(values)

    # Create the response object
    response_body = {"IndexRaw values": response_values}
    logging.info(f"IndexRaw Response body: {response_body}")

    # Return the response
    return func.HttpResponse(json.dumps(response_body), mimetype="application/json")


@app.route(route="GetImageEmbeddings", methods=["POST"])
def GetImageEmbeddings(req: func.HttpRequest) -> func.HttpResponse:
    return vectorize(req)

@app.function_name(name="vectorize")
@app.route(route="vectorize", methods=["POST"])
def vectorize(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("GetImageEmbeddings:Python HTTP trigger function processed a request.")

    # Extract values from request payload
    req_body = req.get_body().decode("utf-8")
    logging.info(f"Request body: {req_body}")
    request = json.loads(req_body)
    values = request["values"]
    response_values = vectorizeImage(values)    

    # Create the response object
    response_body = {"Vectorize values": response_values}

    logging.info(f"Vectorize Response body: {response_body}")

    # Return the response
    return func.HttpResponse(json.dumps(response_body), mimetype="application/json")


@app.function_name(name="search")
@app.route(route="search", methods=["POST"])
def search(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(f"Searching...")
    data = req.get_json()
    logging.info(f"Input data: {data}")

    try:
        user_query = data["query"]
    except KeyError:
        return json.dumps({"error": "The 'query' parameter is required"}), 400
    # query = data.get('query', "woman with computer")
    max_images = data.get("max_images", 5)

    query = ask_openai(user_query)
    logging.info(f"Rephrased query: {query}")

    vector_query = VectorizedQuery(
        vector=generate_embeddings_text(query),
        k_nearest_neighbors=max_images,
        fields="imageVector",
    )

    ssrc = time.time()
    # Perform vector search
    global search_client
    if search_client is None:
        logging.info(f"Creating search client. AI_SEARCH_SERVICE_ENDPOINT: {AI_SEARCH_SERVICE_ENDPOINT}, AI_SEARCH_INDEX_NAME: {AI_SEARCH_INDEX_NAME}, AZURE_SEARCH_ADMIN_KEY: {AZURE_SEARCH_ADMIN_KEY}")
        search_client = SearchClient(
            AI_SEARCH_SERVICE_ENDPOINT,
            AI_SEARCH_INDEX_NAME,
            AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY),
        )

    results = search_client.search(
        search_text=None, vector_queries=[vector_query], select=["title", "imageUrl"]
    )

    logging.info(f"Time taken for florence search: {time.time() - ssrc}")
    # Print the search results
    output = []
    for result in results:
        output.append(
            {
                "Title": result["title"],
                "Image URL": result["imageUrl"],
                "Score": result["@search.score"],
            }
        )
    return json.dumps(output)


def vectorizeImage(values):
    # Process values and generate the response payload
    response_values = []
    for value in values:
        imageUrl = value["data"]["imageUrl"]
        recordId = value["recordId"]
        logging.info(f"Input imageUrl: {imageUrl}")
        logging.info(f"Input recordId: {recordId}")

        # Get image embeddings
        sas_token = helper_functions.create_service_sas_blob(imageUrl)

        vector = helper_functions.get_image_embeddings(imageUrl, sas_token)

        # Add the processed value to the response payload
        response_values.append(
            {
                "recordId": recordId,
                "data": {"vector": vector},
                "errors": None,
                "warnings": None,
            }
        )
    return response_values


def ask_openai(query):
    logging.info(f"Asking OpenAI...")
    logging.info(f"Input query: {query}")

    global chat_client
    if chat_client is None:
        chat_client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=API_VERSION,
        )

    chat_completion = chat_client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are helpful assistant. "},
            {
                "role": "user",
                "content": f"Convert a user query into a textual representation capturing central semantic meanings which is most suitable for finding best results in a search. Output only a final query not more tha 200 tokens size. Here is the original query: {query}",
            },
        ],
        model=OPEN_AI_MODEL,
        max_tokens=200,
    )

    return chat_completion.choices[0].message.content


def generate_embeddings_text(text):

    logging.info(f"Generating embeddings...")
    logging.info(f"Input text: {text}")
    logging.info(f"Input AI_VISION_ENDPOINT: {AI_VISION_ENDPOINT}")

    url = f"{AI_VISION_ENDPOINT}/computervision/retrieval:vectorizeText?api-version=2023-02-01-preview"

    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": AI_VISION_API_KEY,
    }

    data = {"text": text}

    s = time.time()
    response = requests.post(url, headers=headers, json=data)
    logging.info(f"Time taken florence text embedding: {time.time() - s}")

    if response.status_code == 200:
        # logging.info(f"Embeddings: {response.json()}")
        embeddings = response.json()["vector"]
        return embeddings
    else:
        logging.info(f"Error: {response.status_code} - {response.text}")
        return None


