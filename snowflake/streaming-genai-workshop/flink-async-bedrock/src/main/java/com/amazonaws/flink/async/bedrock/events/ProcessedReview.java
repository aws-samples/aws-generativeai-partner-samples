package com.amazonaws.flink.async.bedrock.events;

public class ProcessedReview {

    private int reviewId;
    private String userId;
    private String summary;
    private String originalText;
    private long dateTime;
    private String sentiment;
    private String movieTitle;

    public ProcessedReview() {
    }

    public ProcessedReview(int reviewId, String userId, String summary, String originalText, long dateTime,
            String sentiment, String movieTitle) {
        this.reviewId = reviewId;
        this.userId = userId;
        this.summary = summary;
        this.originalText = originalText;
        this.dateTime = dateTime;
        this.sentiment = sentiment;
        this.movieTitle = movieTitle;
    }

    public int getReviewId() {
        return reviewId;
    }

    public void setReviewId(int reviewId) {
        this.reviewId = reviewId;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String productId) {
        this.summary = summary;
    }

    public String getOriginalText() {
        return originalText;
    }

    public void setOriginalText(String originalText) {
        this.originalText = originalText;
    }

    public long getDateTime() {
        return dateTime;
    }

    public void setDateTime(long dateTime) {
        this.dateTime = dateTime;
    }

    public String getSentiment() {
        return sentiment;
    }

    public void setSentiment(String sentiment) {
        this.sentiment = sentiment;
    }

    public String getMovieTitle() {
        return movieTitle;
    }

    public void setMovieTitle(String movieTitle) {
        this.movieTitle = movieTitle;
    }

    @Override
    public String toString() {
        return "ProcessedReview{" +
                "reviewId=" + reviewId +
                ", userId='" + userId + '\'' +
                ", summary='" + summary + '\'' +
                ", originalText='" + originalText + '\'' +
                ", dateTime=" + dateTime + '\'' +
                ", sentiment=" + sentiment + '\'' +
                ", movieTitle='" + movieTitle + '\'' +
                '}';
    }
}
