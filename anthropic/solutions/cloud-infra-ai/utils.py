import logging
import json

# Setup logging
logging.basicConfig(format='%(levelname)s: %(message)s')
logger = logging.getLogger()

tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "GetECSAmisReleases",
                        "description": "Get Amazon Elastic Container Service (ECS) Amazon Machine Images (AMIs) detail information.",
                        "inputSchema": {
                            "json": {
                                "type": "object",
                                "properties": {
                                    "image_ids": {
                                        "type": "array",
                                        "description": "List of Amazon machine image (AMI) ids"
                                    }
                                },
                                "required": ["image_ids"]
                            }
                        }
                    }
                }
            ]
        }

# Bedrock streaming method
def stream_messages(bedrock_client,
                    model_id,
                    messages,
                    system_text,
                    tool_config=None,
                    stop_sequences=None):
    """
    Sends a message to a model and streams the response.
    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The model ID to use.
        messages (JSON) : The messages to send to the model.
        tool_config : Tool Information to send to the model.

    Returns:
        stop_reason (str): The reason why the model stopped generating text.
        message (JSON): The message that the model generated.
    """
    temperature = 0.5
    inference_config = {"temperature": temperature}
    if stop_sequences is not None:
        inference_config['stopSequences'] = stop_sequences
    logger.info("Streaming messages with model %s", model_id)
    system_prompts = [{"text" : system_text}]
    if tool_config is None:
        response = bedrock_client.converse_stream(
            modelId=model_id,
            messages=messages,
            system=system_prompts,
            inferenceConfig = inference_config
        )
    else:
        response = bedrock_client.converse_stream(
            modelId=model_id,
            messages=messages,
            system=system_prompts,
            toolConfig=tool_config,
            inferenceConfig = inference_config
        )


    stop_reason = ""
 
    message = {}
    content = []
    message['content'] = content
    text = ''
    tool_use = {}


    #stream the response into a message.
    for chunk in response['stream']:
        if 'messageStart' in chunk:
            message['role'] = chunk['messageStart']['role']
        elif 'contentBlockStart' in chunk:
            tool = chunk['contentBlockStart']['start']['toolUse']
            tool_use['toolUseId'] = tool['toolUseId']
            tool_use['name'] = tool['name']
        elif 'contentBlockDelta' in chunk:
            delta = chunk['contentBlockDelta']['delta']
            if 'toolUse' in delta:
                if 'input' not in tool_use:
                    tool_use['input'] = ''
                tool_use['input'] += delta['toolUse']['input']
            elif 'text' in delta:
                text += delta['text']
                if logging.root.level <= logging.INFO:
                    print(delta['text'], end='')
        elif 'contentBlockStop' in chunk:
            if 'input' in tool_use:
                tool_use['input'] = json.loads(tool_use['input'])
                content.append({'toolUse': tool_use})
                tool_use = {}
            else:
                content.append({'text': text})
                text = ''

        elif 'messageStop' in chunk:
            stop_reason = chunk['messageStop']['stopReason']

    return stop_reason, message
