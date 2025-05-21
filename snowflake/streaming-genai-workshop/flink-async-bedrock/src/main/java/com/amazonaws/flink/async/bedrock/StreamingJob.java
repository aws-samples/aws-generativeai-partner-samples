/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.amazonaws.flink.async.bedrock;

import com.amazonaws.flink.async.bedrock.events.ProcessedReview;
import com.amazonaws.flink.async.bedrock.events.Review;
import com.amazonaws.flink.async.bedrock.operators.AsyncBedrockRequest;
import com.amazonaws.flink.async.bedrock.operators.ReviewMapper;
import com.amazonaws.flink.async.bedrock.utils.GsonUtils;
import org.apache.flink.connector.firehose.sink.KinesisFirehoseSink;
import org.apache.flink.streaming.api.datastream.AsyncDataStream;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.connectors.kinesis.FlinkKinesisConsumer;
import org.apache.flink.streaming.connectors.kinesis.config.AWSConfigConstants;
import org.apache.flink.streaming.connectors.kinesis.config.ConsumerConfigConstants;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.streaming.api.environment.LocalStreamEnvironment;

import com.amazonaws.services.kinesisanalytics.runtime.KinesisAnalyticsRuntime;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.util.Properties;
import java.util.concurrent.TimeUnit;

public class StreamingJob {

	private static final Logger LOG = LogManager.getLogger(StreamingJob.class);

	private static DataStream<String> createDataStreamFromKinesis(
			StreamExecutionEnvironment env, Properties applicationProperties) {
		Properties inputProperties = new Properties();
		inputProperties.setProperty(ConsumerConfigConstants.AWS_REGION, applicationProperties.getProperty("REGION"));
		inputProperties.setProperty(ConsumerConfigConstants.STREAM_INITIAL_POSITION, "LATEST"); // "LATEST"

		return env.addSource(new FlinkKinesisConsumer<>(applicationProperties.getProperty("INPUT_STREAM_NAME"),
				new SimpleStringSchema(), inputProperties));
	}

	private static void createFirehoseSink(DataStream<String> filteredProcessedReviewStreamJson, Properties applicationProperties) {
		Properties sinkProperties = new Properties();
		sinkProperties.setProperty(AWSConfigConstants.AWS_REGION, applicationProperties.getProperty("REGION"));
		String firehoseDeliveryStreamName = applicationProperties.getProperty("FIREHOSE_DELIVERY_STREAM");
		filteredProcessedReviewStreamJson.sinkTo(KinesisFirehoseSink.<String>builder()
				.setSerializationSchema(new SimpleStringSchema())
				.setFirehoseClientProperties(sinkProperties)
				.setDeliveryStreamName(firehoseDeliveryStreamName)
				.build());
	}

	private void execute() throws Exception {

		LOG.info("Starting StreamingJob.");
		final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

		Properties applicationProperties;
		if (env instanceof LocalStreamEnvironment) {
			LOG.info("LocalStreamEnvironment.");
			env.setParallelism(1);
			applicationProperties = new Properties();
			applicationProperties.setProperty("REGION", System.getenv("REGION"));
			applicationProperties.setProperty("INPUT_STREAM_NAME", System.getenv("INPUT_STREAM_NAME"));
			applicationProperties.setProperty("FIREHOSE_DELIVERY_STREAM", System.getenv("FIREHOSE_DELIVERY_STREAM"));
		} else {
			LOG.info("CloudStreamEnvironment.");
			applicationProperties = KinesisAnalyticsRuntime.getApplicationProperties().get("FlinkApplicationProperties");
		}

		LOG.info("Creating DataStream from Kinesis.");
		DataStream<String> inputStream = createDataStreamFromKinesis(env, applicationProperties);

		// Map the input string to Review class object
		DataStream<Review> inputReviewStream = inputStream.map(new ReviewMapper()).uid("inputReviewStream");

		// Make asynchronous API call for each Review using RichAsyncFunction
		DataStream<ProcessedReview> processedReviewStream = AsyncDataStream
				.unorderedWait(inputReviewStream, new AsyncBedrockRequest(applicationProperties), 25000, TimeUnit.MILLISECONDS, 1000).uid("processedReviewStream");

		LOG.info("Filter correctly-processed reviews from the stream");
		DataStream<ProcessedReview> filteredProcessedReviewStream = processedReviewStream.filter(
				processedReview -> processedReview.getSentiment().equals("positive")  || processedReview.getSentiment().equals("negative")).uid("filteredProcessedReviewStream");

		LOG.info("Converting processed reviews to JSON");
		DataStream<String> filteredProcessedReviewStreamJson = filteredProcessedReviewStream.map(x -> GsonUtils.toJson(x));

		if (env instanceof LocalStreamEnvironment) {
			filteredProcessedReviewStreamJson.print("processedReviewStreamJson: ");
		} else {
			// Sink to Amazon Kinesis Data Firehose
			String firehoseDeliveryStreamName = applicationProperties.getProperty("FIREHOSE_DELIVERY_STREAM");
			if (firehoseDeliveryStreamName == null || firehoseDeliveryStreamName.isEmpty()) {
				throw new IllegalArgumentException("FIREHOSE_DELIVERY_STREAM property is required");
			}
			LOG.info("Sinking data to Firehose delivery stream: {}", firehoseDeliveryStreamName);
			createFirehoseSink(filteredProcessedReviewStreamJson, applicationProperties);
		}

		env.execute("Executing Flink Job");
	}

	public static void main(String[] args) throws Exception {

		LOG.info("Starting the Flink job.");

		StreamingJob job = new StreamingJob();
		job.execute();

	}
}