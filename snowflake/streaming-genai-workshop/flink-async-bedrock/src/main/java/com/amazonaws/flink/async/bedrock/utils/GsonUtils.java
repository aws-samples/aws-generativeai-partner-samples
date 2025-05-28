package com.amazonaws.flink.async.bedrock.utils;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

/**
 * Utility class for working with Gson.
 */ 
public final class GsonUtils {

  private static final Gson gson = new GsonBuilder()
      .setDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS")
      .create();

  /**
   * Converts the given object to its JSON representation.
   *
   * @param objToConvert the object to convert
   * @param <T> the type of the object
   * @return the JSON representation as a string
   */
  public static <T> String toJson(T objToConvert) {
    return gson.toJson(objToConvert); 
  }
}
