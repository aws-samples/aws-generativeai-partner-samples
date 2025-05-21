package com.amazonaws.flink.async.bedrock.operators;

import com.amazonaws.flink.async.bedrock.events.Review;
import com.google.gson.Gson;
import org.apache.flink.api.common.functions.MapFunction;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class ReviewMapper implements MapFunction<String, Review> {

    private static final Logger LOG = LogManager.getLogger(ReviewMapper.class);
    
    /**
     * Maps a JSON string representation of a review to a Review object.
     *
     * @param s The JSON string representing the review.
     * @return A Review object deserialized from the input JSON string.
     * @throws Exception If an error occurs during the deserialization process.
     */
    @Override
    public Review map(String s) {
        try {
            Gson gson = new Gson();
            return gson.fromJson(s, Review.class);
        } catch (Exception e) {
            LOG.error(e.getMessage());
            throw e;
        }
    }
}
