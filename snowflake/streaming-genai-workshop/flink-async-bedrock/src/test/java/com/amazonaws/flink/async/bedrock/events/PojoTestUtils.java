package com.amazonaws.flink.async.bedrock.events;


import org.apache.flink.api.common.ExecutionConfig;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.api.common.typeutils.TypeSerializer;
import org.apache.flink.api.java.typeutils.TypeExtractor;
import org.apache.flink.api.java.typeutils.runtime.PojoSerializer;

import static org.assertj.core.api.AssertionsForClassTypes.assertThat;

// Inspired by: https://issues.apache.org/jira/browse/FLINK-28636 /
public class PojoTestUtils {

    public static <T> void assertSerializedAsPojoWithoutKryo(Class<T> clazz) throws AssertionError {
        final ExecutionConfig executionConfig = new ExecutionConfig();
        executionConfig.enableGenericTypes();

        final TypeInformation<T> typeInformation = TypeInformation.of(clazz);
        final TypeSerializer<T> actualSerializer;
        try {
            actualSerializer = typeInformation.createSerializer(executionConfig);
        } catch (UnsupportedOperationException e) {
            throw new AssertionError(e);
        }

        assertThat(actualSerializer)
                .withFailMessage(
                        "Instances of the class '%s' cannot be serialized as a POJO, but would use a '%s' instead. %n"
                                + "Re-run this test with INFO logging enabled and check messages from the '%s' for possible reasons.",
                        clazz.getSimpleName(),
                        actualSerializer
                                .getClass()
                                .getSimpleName(),
                        TypeExtractor.class.getCanonicalName())
                .isInstanceOf(PojoSerializer.class);
    }
}