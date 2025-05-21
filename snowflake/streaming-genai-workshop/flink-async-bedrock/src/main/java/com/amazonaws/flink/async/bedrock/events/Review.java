package com.amazonaws.flink.async.bedrock.events;

import java.util.Arrays;
import java.util.List;

import com.google.gson.JsonElement;
import com.google.gson.annotations.SerializedName;


public class Review {
    @SerializedName("review_id")
    private int reviewId;
    @SerializedName("user_id")
    private String userId;
    @SerializedName("text")
    private String text;
    @SerializedName("date_time")
    private long dateTime;
    @SerializedName("movie_title")
    private String movieTitle;

    public Review() {
    }

    public Review(int reviewId, String userId, String text, long dateTime, String movieTitle) {
        this.reviewId = reviewId;
        this.userId = userId;
        this.text = text;
        this.dateTime = dateTime;
        this.movieTitle = movieTitle;
    }

    public int getReviewId() {
        return reviewId;
    }

    public void setReviewId(int sessionId) {
        this.reviewId = sessionId;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public String getText() {
        return text;
    }

    public void setText(String productId) {
        this.text = text;
    }

    public long getDateTime() {
        return dateTime;
    }
    public void setDateTime(long dateTime) {
        this.dateTime = dateTime;
    }

    public String getMovieTitle() {
        return movieTitle;
    }

    public void setMovieTitle(String movieTitle) {
        this.movieTitle = movieTitle;
    }


    public static List<String> getHardcodedReviewsAsString() {
        return Arrays.asList(
                "{\"user_id\": \"61707b68-d3df-4537-bdf5-776b61edeb60\", \"review_id\": 123, \"date_time\": 1706172121, \"text\": \"One of Boris Karloff's real clinkers. Essentially the dying Karloff (looking about 120 years older than he was)is a scientist in need of cash to finish his experiments before he dies. Moving from Morocco where his funding is taken over by someone else he goes to the South of France where he works a s physician while trying to scrap enough money to prove his theories. Desperate for money he makes a deal with the young rich wife of a cotton baron who is dying. She will fund him if he helps her poison the husband so she can take his money and carry on with a gigolo (who I think is married). If you think I got that from watching the movie you're wrong, I had to read what other people posted to figure out happened. Why? because this movie had me lost from two minutes in.I had no idea what was going on with its numerous characters and multiple converging plot lines. Little is spelled out and much isn't said until towards the end by which time I really didn't care. Its a dull mess of interest purely for Karloff's performance which is rather odd at times. To be honest this is the only time I've ever seen him venture into Bela Lugosi bizarre territory. Its not every scene but a few and makes me wonder how much they hung out.\", \"movie_title\": \"The Sorcerers\"}"
        );
    }

    @Override
    public String toString() {
        return "Review{" +
                "reviewId=" + reviewId +
                ", userId='" + userId + '\'' +
                ", text='" + text + '\'' +
                ", dateTime=" + dateTime +
                ", movieTitle='" + movieTitle + '\'' +
                '}';
    }
}