# Hybrid Geo Spatial RAG with Elastic Search and Amazon Bedrock

## About
In this streamlit application you will see how to use Elastic search, Amazon Bedrock, Anthropic Claude 3 and Langchain to build a Retrieval Augmented Generation (RAG) solution that leverages Geospatial features of Elastic.

This application introduces an interactive AI agent designed to assist with real estate inquiries. Users looking to purchase properties, such as townhomes, condos, or single-family homes in specific locations (e.g., New York, NY or Cupertino, CA) can use the agent to find listings that match their preferences. These preferences can include factors like city, distance, property type, and desired amenities such as a swimming pool or lawn.

## Hybrid Geo Spatial RAG - System Architecture
![alt text](./geo-spatial-RAG-architecture.png).

### Architecture Details

1. User enters a prompt in natural human language (English in this case), asking a question about a real estate properties user is looking for. Example:
- Find me homes near Frisco, TX.
- Find me luxury condos in Cupertino, CA within 15 miles distance that has a private balcony and that is just near to Apple campus. I would like spa or sauna along with clubhouse facilities. An outdoor pools is even great. However, I want HOA fees per year not to exceed $10K.

2. Conversational AI assistant forwards this user question to an Amazon API Gateway.

3. Amazon API Gateway further forwards this query to a Lambda function that processes this request.

4. Lambda function forwards the query to Amazon Bedrock LLMs. Anthropic Claude Sonnet LLM is employed to do NER (Named entitity recognition). Amazon Titan LLM is also employed to vectorize (create embeddings) from input prompt. This is particularly need to run Vector Similarity Search.

5. Named entity recognitions for search property type (Ex: Condo, Townhouse etc), for search address, property features, distance etc are extracted.

6. Lambda recieves these entities that are extracted.

7. Lambda further passes this information to Amazon Location Services to geocode the search address.

8. The output from Amazon Location Services is the geocoded physical addresses translated into a pair of longitude and latitude. This information is what is required to do run geo spatial queries using Elasticsearch.

9. Geo-coded long, lat information is passed back to AWS Lambda function.

10. Geospatial Hybrid Query: AWS Lambda runs a hybrid geo spatial query against the elastic database

11. The results that contains the search property listings is passed back to lambda function.

12. RAG: The results are passed to the Amazon Bedrock LLMs as an additional contextual knowledge base.

13. The response from the Amazon Bedrock LLMs is passed all the way back to the end user as completion of response ( See #13, #14, $15, $16 annotations in the picture)

17. Optionally, an email of the entire listings can be passed to the user in an email, using Amazon SES

## Setup instructions

### Setup EC2 instance

1. Spinup an EC2 instance in AWS. Choose `Amazon Linux` as your platform choice.
2. Enable security group and enable inbound traffic for SSH (Port 22) and for streamlit application (Port 8501)
3. Attach an `IAM Role` that has the following policies.
    a. `AmazonBedrockFullAccess` 
    b. A custom policy with the following definitions.
    ```
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "VisualEditor0",
                "Effect": "Allow",
                "Action": [
                    "geo:ListKeys",
                    "geo:ListMaps",
                    "geo:ListTrackers",
                    "geo:ListRouteCalculators",
                    "geo:*",
                    "geo:ListGeofenceCollections",
                    "geo:ListPlaceIndexes"
                ],
                "Resource": "*"
            }
        ]
    }
    ```
### Configuration of Elastic endpoints
Clone this repo first.
Update the `config.yaml` file with the following details
- cloud_id
- cloud_api_key
- index_name

### Data loader
Elastic Developer Tools Web Console Method:
- Login into your Elastic Cloud's account
- Access Developer Tool console.
- Paste the contents of `data-loader-elastic-console.txt` in to the developer tool console.
- Edit AWS configuration settings such as `aws_access_key` and `aws_secret_key`.
- Start running each of the API calls in Elastic Cloud's Developer console.

### Run streamlit app

0. Clone this repo. And change directory in to this folder.
```
git clone https://github.com/aws-samples/aws-generativeai-partner-samples.git
cd aws-generativeai-partner-samples/ 
```

1. Enable python virtual environment.

```
python3 -m venv geospatial-rag-streamlit-app.venv
source geospatial-rag-streamlit-app.venv/bin/activate
```

2. Upgrade pip
```
pip install --upgrade pip
```

3. Install all python libraries.
```
pip install -r requirements.txt
```

4. Run the app
```
streamlit run geo-spatial-rag-elastic-bedrock.py
```
The output may look like this:

```
$ streamlit run geo-spatial-rag-elastic-bedrock.py

Collecting usage statistics. To deactivate, set browser.gatherUsageStats to false.


  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://172.31.16.251:8501
  External URL: http://3.91.65.220:8501

```

5. Open the URL to access the app. 
