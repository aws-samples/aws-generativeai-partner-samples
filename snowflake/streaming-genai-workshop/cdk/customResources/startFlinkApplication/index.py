import boto3
import logging
import os
import json
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('kinesisanalyticsv2')

def on_event(event, context):
    logger.info(event)
    request_type = event['RequestType']
    match request_type:
        case 'Create':
            return start_app(event)
        case 'Update':
            return update_app(event)
        case 'Delete':
            return delete_app(event)
        case _:
            logger.error(f'Unexpected RequestType: {event["RequestType"]}')

    return


def start_app(event):
    logger.info('Starting FlinkApplication')
    app_name = event['ResourceProperties']['AppName']
    description_response = client.describe_application(ApplicationName=app_name)
    status = description_response['ApplicationDetail']['ApplicationStatus']
    if status == "READY":
        client.start_application(ApplicationName=app_name)
    while (True):
        description_response = client.describe_application(ApplicationName=app_name)
        status = description_response['ApplicationDetail']['ApplicationStatus']
        if status != "STARTING":
            if status != "RUNNING":
                raise Exception(f"Unable to start the app in state: {status}")
            logger.info(f"Application status changed: {status}")
            break
        else:
            time.sleep(1)

def update_app(event):
    raise NotImplementedError

def delete_app(event):
    logger.info('Starting FlinkApplication')
    app_name = event['ResourceProperties']['AppName']
    description_response = client.describe_application(ApplicationName=app_name)
    status = description_response['ApplicationDetail']['ApplicationStatus']
    if status == "RUNNING":
        client.stop_application(ApplicationName=app_name, Force=True)


