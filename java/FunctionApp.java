import com.azure.core.credential.AzureKeyCredential;
import com.azure.search.documents.SearchClient;
import com.azure.search.documents.SearchClientBuilder;
import com.azure.search.documents.models.SearchOptions;
import com.azure.search.documents.models.SearchResult;
import com.azure.search.documents.models.VectorQuery;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;

@RestController
public class FunctionApp {

    private static final String AI_SEARCH_SERVICE_ENDPOINT = "your_search_service_endpoint";
    private static final String AI_SEARCH_INDEX_NAME = "your_search_index_name";
    private static final String AZURE_SEARCH_ADMIN_KEY = "your_search_admin_key";
    private static SearchClient searchClient;

    @PostMapping("/vectorize")
    public ResponseEntity<String> vectorize(@RequestBody String reqBody) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            JsonNode request = mapper.readTree(reqBody);
            JsonNode values = request.get("values");

            List<JsonNode> responseValues = vectorizeImages(values);

            ObjectNode responseBody = mapper.createObjectNode();
            responseBody.set("values", mapper.valueToTree(responseValues));

            return ResponseEntity.ok(responseBody.toString());
        } catch (Exception e) {
            e.printStackTrace();
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(e.getMessage());
        }
    }

    @PostMapping("/search")
    public ResponseEntity<String> search(@RequestBody String reqBody, @RequestHeader Map<String, String> headers) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            JsonNode data = mapper.readTree(reqBody);

            String userQuery = data.get("query").asText();
            int maxImages = data.has("max_images") ? data.get("max_images").asInt() : 5;

            String query = askOpenAI(userQuery);
            VectorQuery vectorQuery = new VectorQuery(generateEmbeddingsText(query), maxImages, "imageVector");

            if (searchClient == null) {
                searchClient = new SearchClientBuilder()
                        .endpoint(AI_SEARCH_SERVICE_ENDPOINT)
                        .indexName(AI_SEARCH_INDEX_NAME)
                        .credential(new AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY))
                        .buildClient();
            }

            SearchOptions options = new SearchOptions().setSelect("title", "imageUrl");
            Iterable<SearchResult> results = searchClient.search(null, options, vectorQuery);

            List<ObjectNode> output = new ArrayList<>();
            String authHeader = headers.get("Authorization");

            for (SearchResult result : results) {
                String imageUrl = result.getDocument().get("imageUrl").toString();
                String sasToken = createServiceSasBlob(imageUrl);
                String sasUrl = imageUrl + "?" + sasToken;

                ResponseEntity<byte[]> response = restTemplate.getForEntity(sasUrl, byte[].class, authHeader);
                String base64Image = response.getStatusCode() == HttpStatus.OK
                        ? Base64.getEncoder().encodeToString(response.getBody())
                        : "Failed to download image. Status code: " + response.getStatusCode();

                ObjectNode resultNode = mapper.createObjectNode();
                resultNode.put("Title", result.getDocument().get("title").toString());
                resultNode.put("Image URL", imageUrl);
                resultNode.put("Image", base64Image);
                resultNode.put("Score", result.getScore());

                output.add(resultNode);
            }

            return ResponseEntity.ok(mapper.writeValueAsString(output));
        } catch (Exception e) {
            e.printStackTrace();
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(e.getMessage());
        }
    }

    private List<JsonNode> vectorizeImages(JsonNode values) {
        // Implement the logic to vectorize images
        return new ArrayList<>();
    }

    private String askOpenAI(String query) {
        // Implement the logic to ask OpenAI
        return "";
    }

    private String generateEmbeddingsText(String text) {
        // Implement the logic to generate embeddings text
        return "";
    }

    private String createServiceSasBlob(String imageUrl) {
        // Implement the logic to create SAS token
        return "";
    }
}