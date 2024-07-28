# Vector Image Search using Azure OpenAI with Azure AI Search
![Diagram](/readme/diagram_vector_search.png)

## Introduction
Vector image search is revolutionizing the way we search and retrieve images by leveraging the power of AI. This article delves into how [Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-services/openai/overview) and [Azure AI Search](https://learn.microsoft.com/en-us/azure/search/search-what-is-azure-search) can be combined to create an efficient vector image search solution. We will cover the setup, deployment, and usage of these services to provide a comprehensive guide for AI developers and engineers.

> We dive into the core functionalities of the Azure AI Search service, focusing on the ***search*** and ***vectorize*** methods in the [function_app.py](/function_app.py) python file. These methods are pivotal in integrating Azure's AI services to perform vector image searches.


## Scenario Overview
Imagine having a vast collection of images and needing to find similar ones based on content rather than metadata. This is where vector image search comes in. By converting images into vector representations, we can perform similarity searches with high accuracy, making it ideal for various applications such as e-commerce, digital asset management, and more.


## Prerequisites
* An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/).
* An Azure Storage account for storing images. [Create a storage account](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-create?tabs=azure-portal).
* An Azure AI Search service for any tier and any region [Create a service](https://learn.microsoft.com/en-us/azure/search/search-create-service-portal) or [find an existing service](https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.Search%2FsearchServices) under your current subscription.
* An Azure OpenAI service for any tier and any region. [Create a service](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/create-resource?pivots=web-portal)
* Azure Functions setup for processing [Create python function](https://learn.microsoft.com/en-us/azure/azure-functions/functions-create-function-app-portal?pivots=programming-language-python)
* Tools: Azure CLI, Visual Studio Code, and Postman for API testing


## AI Search Setup
![Search and Indexer](/readme/skillset-process-diagram-1.png)
Below are Azure AI Search schema files that define the **index**, **indexer**, and **skillset** used to store and process image data for efficient search and retrieval. These files are used to configure the Azure AI Search service to work with the vector image search solution. 

**Open the Azure AI Search service** in the Azure portal and navigate to each section to upload the corresponding JSON file.

#### 1. Create Index  
This defines the structure and schema of the search index, including specifying fields, data types, and attributes. 
Go to the Indexes blade and create a new index using the JSON definition file [vector-image-index-db.json](/artifacts/vector-image-index-db.json).
![Index](/readme/azure-search-index-setup.png)

#### 2. Create Indexer
Set up an indexer to manage data ingestion from a source like Azure Storage to the search index. Use the [vector-image-indexer.json](/artifacts/vector-image-indexer.json) file in the Indexers blade to create a new indexer.
![Indexer](/readme/azure-search-indexer-setup.png)

#### 3. Create Skillset
Create a skillset to define the AI enrichment pipeline for image processing before indexing. Use the JSON definition file [vector-image-skillset.json](/artifacts/vector-image-skillset.json) to create a new skillset in the Skillsets blade.
![Skillset](/readme/azure-search-skillset-setup.png)

These components work together to enable the ingestion, transformation, and indexing of image data, allowing efficient search and retrieval using Azure AI Search service, with **the indexer triggering the vectorize Azure Function for handling image embeddings**.  


## Azure Function Setup 


#### Variables
Configuration variables are stored in the [local.settings.json](/local.settings.json) file and should be set as part of the Azure Function Rnvironment variables blase.
Key variables to configure include:

```
AZURE_OPENAI_API_KEY:<Your Azure OpenAI API Key>,
AZURE_OPENAI_ENDPOINT:<Your Azure OpenAI Endpoint>,
OPEN_AI_MODEL:gpt-35-turbo, 
API_VERSION:2024-02-01,
AI_VISION_ENDPOINT:<Your Azure Vision Endpoint>,
AI_VISION_API_KEY:<Your Azure Vision API Key>,
AI_SEARCH_SERVICE_ENDPOINT:<Your Azure Search Service Endpoint>,
AZURE_SEARCH_ADMIN_KEY:<Your Azure Search Admin Key>,
AI_SEARCH_INDEX_NAME:<Your Azure Search Index Name>,
ACCOUNT_KEY:<Your Account Key>,
```
![Variables](/readme/azure-function-env-vars.png)


#### GitHub Action Workflow
The function is being deployed automaticlly using a GitHub Action workflow. The function app is responsible for processing image data and performing similarity searches using Azure AI Search. The function app consists of two main methods: ***vectorize*** and ***search***.  

The [main-premium.yml](/.github/workflows/main-premium.yml) GitHub Action workflow file automates the deployment of the function app. It triggers the deployment process whenever changes are pushed to the main branch. The workflow uses the Azure Functions action to deploy the function app to Azure.  

For the workflow to work, you need to set up the following secrets in your GitHub repository:  
* ***AZURE_RBAC_CREDENTIALS***: Azure service principal credentials with access to the Azure subscription.  
* ***AZURE_FUNCTIONAPP_PUBLISH_PROFILE_PREMIUM***: Publish profile for the Azure Function app.  


## Testing the Solution
#### *vectorize*
Uploading Files to the storage and then running the Azure AI search Indexer for embedding generation.  

* Use Azure Storage Explorer or Azure CLI for uploading images to the container.  
* Goto your AI Search service, run the indexer to process and vectorize images.  
* Monitor the indexing process via Azure Portal.  

#### *search*
Using the Search API to Vector Search for Images, Leverage the Azure Search API to perform vector searches.  

* Construct the search query with the image vector {query: "blue sky"}.  
* Execute the query using Postman or code.  
* Interpret the search results to find similar images.  


## Azure Function Explained

### The *vectorize* Method
The *vectorize* method is responsible for converting images into vector embeddings. This process involves several steps:

#### 1. HTTP Request Handling:
* The method is triggered by a POST request containing image URLs and other metadata.  
* The request body is parsed to extract the values needed for processing.  

#### 2. Image Embedding Generation:
* The ***vectorize_images*** function is called with the extracted values. This function processes each image URL by invoking the ***vectorize_image*** helper function.  
* Within ***vectorize_image***, a SAS token is created for secure access to the image stored in Azure Blob Storage.  
* The ***get_image_embeddings*** function from the helper module generates the embeddings using Azure's Computer Vision API. The embeddings are numerical representations capturing the semantic content of the images.
#### 3. Response Construction:

* The embeddings are assembled into a response payload.  
* The response is returned as a JSON object, making the embeddings available for downstream tasks such as indexing and searching.  

By leveraging Azure's Computer Vision API, the ***vectorize*** method transforms images into vectors. These vectors are numeric representations that encapsulate the images' visual features, making them suitable for similarity searches.  

#### Usage
```
# Example usage
image_urls = ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
embeddings = vectorize_images(image_urls)
print(embeddings)
```

### The *search* Method
The search method facilitates image similarity searches using vectors generated by the vectorize method. Here's how it works:

#### 1. HTTP Request Handling:
* The method is triggered by a POST request containing a query string and optional parameters like *max_images*.  

#### 2. Query Processing with OpenAI:
* The provided query is refined using the ***ask_openai*** function, which interacts with Azure OpenAI. This function rephrases the query to improve search accuracy.  
* The refined query is then converted into vector embeddings using the ***generate_embeddings_text*** function. This function utilizes Azure's Computer Vision API to generate text embeddings.  

#### 3. Vector Search Execution:
* A ***VectorizedQuery*** object is created, containing the query embeddings and parameters for the search.  
* The ***search_client*** performs a vector search on the image vectors stored in the Azure AI Search index. This search identifies images whose vector embeddings are most similar to the query embeddings.  

#### 4. Result Compilation:
* The search results are compiled into a response payload. For each result, a SAS token is generated for secure access to the image.
* The response is returned as a JSON object, containing the image URLs, titles, and search scores.  

The ***search*** method integrates Azure OpenAI and Azure AI Search to perform efficient and accurate image similarity searches. By converting textual queries into vector embeddings, it ensures that the search results are relevant and precise.

## Usage
```
# Example usage
query = "Find images of mountains"
search_results = search_images(query, max_images=5)
print(search_results)
```

## Azure Resources
The azure-ai-vision-search repository leverages several Azure services to enable vector image searches:
![Azure Resources](/readme/azure-resources.png)

## Conclusion
Combining [Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-services/openai/overview) with [Azure AI Search](https://learn.microsoft.com/en-us/azure/search/search-what-is-azure-search) provides a powerful solution for vector image search. By following this guide, you can set up and deploy a robust search system to meet various business needs. Explore further possibilities by integrating more advanced AI models and expanding your search capabilities.

