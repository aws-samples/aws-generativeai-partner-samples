package com.amazonaws.flink.async.bedrock.operators;

import com.amazonaws.flink.async.bedrock.events.ProcessedReview;
import com.amazonaws.flink.async.bedrock.events.Review;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.async.ResultFuture;
import org.apache.flink.streaming.api.functions.async.RichAsyncFunction;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.json.JSONException;
import org.json.JSONObject;
import org.json.JSONArray;
import software.amazon.awssdk.core.SdkBytes;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeAsyncClient;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelRequest;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelResponse;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Properties;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

public class AsyncBedrockRequest extends RichAsyncFunction<Review, ProcessedReview> {

    private static final Logger LOG = LogManager.getLogger(AsyncBedrockRequest.class);
    private transient BedrockRuntimeAsyncClient client;
    private final Properties applicationProperties;

    public AsyncBedrockRequest(Properties applicationProperties) {
        this.applicationProperties = applicationProperties;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        client = BedrockRuntimeAsyncClient.builder().region(Region.of(applicationProperties.getProperty("REGION"))).build();
    }

    @Override
    public void close() throws Exception {
        if (client != null) {
            client.close();
        }
    }

    /**
     * Asynchronously invokes the Anthropic Claude language model to process a given review.
     *
     * @param review The review to be processed.
     * @param resultFuture A future object to hold the result of the model invocation.
     * @throws Exception If an error occurs during the model invocation process.
     */
    @Override
    public void asyncInvoke(Review review, final ResultFuture<ProcessedReview> resultFuture) throws Exception {

        String reviewText = review.getText();

        String systemPrompt = "Summarize the review within the <review> tags into a single and concise sentence alongside the sentiment that is either positive or negative. Return a valid JSON object with following keys: summary, sentiment. <example> {\\\"summary\\\": \\\"The reviewer strongly dislikes the movie, finding it unrealistic, preachy, and extremely boring to watch.\\\", \\\"sentiment\\\": \\\"negative\\\"} </example>";

        JSONObject user_message = new JSONObject()
            .put("role", "user")
            .put("content", "<review>" + reviewText + "</review>");

        JSONObject assistant_message = new JSONObject()
            .put("role", "assistant")
            .put("content", "{");

        JSONArray messages = new JSONArray()
                .put(user_message)
                .put(assistant_message);

        String payload = new JSONObject()
                .put("system", systemPrompt)
                .put("anthropic_version", "bedrock-2023-05-31")
                .put("temperature", 0.0)
                .put("max_tokens", 4096)
                .put("messages", messages)
                .toString();

        InvokeModelRequest request = InvokeModelRequest.builder()
                .body(SdkBytes.fromUtf8String(payload))
                .modelId("anthropic.claude-3-haiku-20240307-v1:0")
                .build();

        CompletableFuture<InvokeModelResponse> completableFuture = client.invokeModel(request)
                .whenComplete((response, exception) -> {
                    if (exception != null) {
                        LOG.error("Model invocation failed: " + exception);
                    }
                })
                .orTimeout(250000, TimeUnit.MILLISECONDS);

        CompletableFuture.supplyAsync(new Supplier<ProcessedReview>() {

            @Override
            public ProcessedReview get() {
                try {
                    InvokeModelResponse response = completableFuture.get();
                    LOG.info(response.body().asUtf8String());
                    JSONObject responseObject = new JSONObject(response.body().asUtf8String());
                    JSONArray contentArray = responseObject.getJSONArray("content");
                    JSONObject textObject = contentArray.getJSONObject(0);
                    String responseString = textObject.getString("text");

                    // Add as we put words in Claude's mouth
                    responseString = "{" + responseString;
                    LOG.info("ResponseString: " + responseString);

                    JSONObject responseJson = new JSONObject(responseString);
                    return new ProcessedReview(review.getReviewId(), review.getUserId(), responseJson.get("summary").toString(), review.getText(), review.getDateTime(), responseJson.get("sentiment").toString(), review.getMovieTitle());

                } catch (InterruptedException | ExecutionException | JSONException e ) {
                    LOG.error(e.getMessage());
                    // Create String that says Summary not available
                    return new ProcessedReview(review.getReviewId(), review.getUserId(), "Summary not available", review.getText(), review.getDateTime(), "error", review.getMovieTitle());
                }
            }
        }).thenAccept( (ProcessedReview result) -> {
            resultFuture.complete(Collections.singleton(result));
        });
    }
}
