import json
import os
import sys
import boto3 
import time
import pprint
from datasets import load_dataset
import random
import jsonlines
from utils import aws_utils
import pymongo
from collections import defaultdict
from bson import ObjectId

bucket_name='fine-tune-embeddings-mongo'
session = boto3.session.Session()

#get region from session
region = session.region_name

s3_client = boto3.client('s3', region_name = region)
bedrock = boto3.client(service_name="bedrock", region_name = region)
bedrock_runtime = boto3.client(service_name="bedrock-runtime", region_name = region )

#following are the features of the dataset:
#_id,plot,genres,runtime,rated,cast,poster,title,fullplot,languages,released,directors,writers,awards,wins,nominations,text,lastupdated,year,imdb,rating,votes,id,countries,type,tomatoes,viewer,rating,numReviews,meter,dvd,critic,rating,numReviews,meter,lastUpdated,rotten,production,fresh,num_mflix_comments,


def flatten_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        #if key contains poster/fullplot, skip it
        if "poster" in k:
            continue
        if "fullplot" in k:
            continue
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        elif isinstance(v, list):
            items.extend(flatten_list(v, new_key, sep).items())
        else:
            if v:
                items.append((new_key, v))
    return dict(items)

def flatten_list(l, parent_key, sep):
    flattened = defaultdict(list)
    for idx, item in enumerate(l):
        new_key = f"{parent_key}{sep}{idx}"
        if isinstance(item, dict):
            flattened.update(flatten_dict(item, new_key, sep))
        elif isinstance(item, list):
            flattened.update(flatten_list(item, new_key, sep))
        else:
            flattened[new_key] = item
    return flattened


for model in bedrock.list_foundation_models(
    byCustomizationType="FINE_TUNING")["modelSummaries"]:
    for key, value in model.items():
        print(key, ":", value)
    print("-----\n")
    

# mongo_uri = os.environ.get('ATLAS_URI')
mongo_uri = aws_utils.get_secret("workshop/atlas_secret")
print("got credentials..."+ mongo_uri )
# Connect to the MongoDB database
client = pymongo.MongoClient(mongo_uri)
print("connected to mongoDB...")
db = client["sample_mflix"]
collection = db["movies"]


#get count of documents
count = collection.count_documents({})
print(count)

#for the lab we will use only 1000 documents to train
documents = collection.find().limit(1000)

#flatten the documents
flattened_documents = []
for document in documents:
    flattened_document = flatten_dict(document)
    flattened_documents.append(flattened_document)

json_data = json.dumps(flattened_documents, default=str)

#save the json file
with open("sample_document.json", "w") as f:
    f.write(json_data)

try:
    #load the json file
    data = load_dataset("json", data_files="sample_document.json")

except Exception as e:
    print(e)

#split the dataset between train, test and validation
train_test_split = data["train"].train_test_split(test_size=0.2)
#80 percent of the data for training
train_data = train_test_split["train"]
#split the remaining 50-50 between test and validation.
test_data = train_test_split["test"]
validation_data = test_data.train_test_split(test_size=0.5)["test"]

#Prepare the datasets train, test and valid in the format required for fine tuning
#Format to be used:{"prompt": "<prompt1>", "completion": "<expected generated text>"}


def jsonl_converter(dataset,file_name):
     with jsonlines.open(file_name, 'w') as writer:
        for line in dataset:
            # Convert the line to a JSON string to check its length. Sum of input and output tokens for batch size 1 is 4096.
            #refer details here https://docs.aws.amazon.com/bedrock/latest/userguide/quotas.html#quotas-model-customization
            json_string = json.dumps(line)
            # if len(json_string) < 2048:
            #     # If so, write the line to the file
            writer.write(line)


dataset_train_format=[]
for dp in train_data:
    temp_dict={}
    #get title  from the dataset
    temp_dict['prompt']= dp['title']
    dp= str(dp)
    temp_dict['completion']= dp
    dataset_train_format.append(temp_dict)
    
dataset_test_format=[]
for dp in test_data:
    temp_dict={}
    temp_dict['prompt']= dp['title']
    dp= str(dp)
    temp_dict['completion']= dp
    dataset_test_format.append(temp_dict)

dataset_valid_format=[]
for dp in validation_data:
    temp_dict={}
    temp_dict['prompt']= dp['title']
    dp= str(dp)
    temp_dict['completion']= dp
    dataset_valid_format.append(temp_dict)
    

#save he datasets in jsonl format
jsonl_converter(dataset_test_format, 'dataset_test.jsonl')
jsonl_converter(dataset_train_format, 'dataset_train.jsonl')
jsonl_converter(dataset_valid_format, 'dataset_valid.jsonl')




# Create S3 bucket for storing the datasets 
s3bucket = s3_client.create_bucket(Bucket=bucket_name)


#upload the datasets to S3
s3_client.upload_file('dataset_train.jsonl', bucket_name, 'train/dataset_train.jsonl')
s3_client.upload_file('dataset_test.jsonl', bucket_name, 'test/dataset_test.jsonl')
s3_client.upload_file('dataset_valid.jsonl', bucket_name, 'valid/dataset_valid.jsonl')
print("uploaded the datasets to S3")

