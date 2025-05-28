#!/usr/bin/env node

/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { App }from 'aws-cdk-lib';
import {MainStack, MainStackProps} from '../lib/main';

const app = new App();

const mainStackProps: MainStackProps = {
    kinesisStreamName: 'generative-ai-stream',
    flinkAppName: 'generative-ai-flink-application',
    env: {
        region: 'us-west-2'
    }
}

// https://docs.aws.amazon.com/cdk/v2/guide/parameters.html#parameters-about
const snowflakeProps = app.node.tryGetContext('snowflake');
if (snowflakeProps) {
    // Check for required Snowflake properties
    // https://docs.aws.amazon.com/firehose/latest/dev/create-destination.html#create-destination-snowflake
    // https://docs.aws.amazon.com/firehose/latest/dev/secrets-manager-whats-secret.html
    if (!snowflakeProps.secretName || !snowflakeProps.accountUrl || !snowflakeProps.database || !snowflakeProps.table || !snowflakeProps.schema) {
        throw new Error('Snowflake properties are missing or invalid.');
    }
    // Assign properties to SnowflakeStackProps
    const firehoseStreamName = 'generative-ai-firehose';
    const snowflakeSecretName = snowflakeProps.secretName;
    const snowflakeAccountUrl = snowflakeProps.accountUrl;
    const snowflakeDatabase = snowflakeProps.database;
    const snowflakeTable = snowflakeProps.table;
    const snowflakeSchema = snowflakeProps.schema;

    const snowflakeStackProps: MainStackProps = { ...mainStackProps,
        snowflakeConnection: {
            firehoseStreamName: firehoseStreamName,
            snowflakeSecretName: snowflakeSecretName,
            snowflakeAccountUrl: snowflakeAccountUrl,
            snowflakeDatabase: snowflakeDatabase,
            snowflakeTable: snowflakeTable,
            snowflakeSchema: snowflakeSchema
        }
    };
    new MainStack(app, 'StreamingGenerativeAIStack', snowflakeStackProps);
} else {
    new MainStack(app, 'StreamingGenerativeAIStack', mainStackProps);
}
