package com.amazonaws.flink.async.bedrock.events;

import org.junit.jupiter.api.Test;

class ProcessedReviewTest {

    @Test
    public void testAssertSerializedAsPojoWithoutKryo() {
        PojoTestUtils.assertSerializedAsPojoWithoutKryo(ProcessedReview.class);
    }

}