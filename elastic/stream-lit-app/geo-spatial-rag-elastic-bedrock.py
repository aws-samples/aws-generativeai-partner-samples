import streamlit as st

import time
import re
import json
import os
import sys
import boto3
import botocore
import nltk
import pandas as pd
import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models.bedrock import BedrockChat
from langchain.embeddings import BedrockEmbeddings
from botocore.client import Config
from langchain_community.retrievers import AmazonKnowledgeBasesRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_elasticsearch import ElasticsearchStore
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from langchain.schema.runnable import RunnablePassthrough
from langchain.chains import RetrievalQA
from getpass import getpass
from langchain.prompts import PromptTemplate
from langchain.document_loaders import DirectoryLoader
from pathlib import Path
from typing import Dict
from langchain_elasticsearch import ElasticsearchRetriever
from elasticsearch import Elasticsearch
from streamlit_folium import folium_static
import folium


## Debug flag
debug = False

## Elastic Connectivity
# Update config.yaml file with elastic endpoint configurations before trying this app.
# Load configurations 
with open('config.yaml') as f:
    config = yaml.safe_load(f)

cloud_id = config['cloud_id']
cloud_api_key = config['cloud_api_key']
index_name = config['index_name']

els_client = Elasticsearch(
    cloud_id=cloud_id,
    api_key=cloud_api_key
)

## Amazon Bedrock connectivity boiler plate code
bedrock_config = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0})
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
modelId = 'anthropic.claude-3-sonnet-20240229-v1:0' # change this to use a different version from the model provider
embeddingmodelId = 'amazon.titan-embed-text-v1' # change this to use a different embedding model

llm = BedrockChat(model_id=modelId, client=bedrock_client)
embeddings = BedrockEmbeddings(model_id=embeddingmodelId,client=bedrock_client)

user_prompt_template = """
Human: You will be acting as a Real estate realtor. Your end users will ask questions about finding properties near to a specific location given in the form of an address. This address may sometimes contains the Street number, Street Name, City name, State name and zip code. If the country name is not mentioned, consider it as USA.  For the prompt, extract the longitude and latitude information by geocoding.

For example, for the prompt below:

<prompt>
Get me townhomes within 5 miles near 2379 Flicker Street, Frisco, TX 75034. I want the townhome to have a swimming pool in the backyard and kitchen bigger.
</prompt>

Based on the above prompt, the property type the user is looking for is : townhomes. Return this as search_property_type in the JSON output.
address is : 2379 Flicker Street, Frisco, TX 75034. Return this as search_property_address in the JSON output.
radius is : 5mi
Return this as search_property_radius in the JSON output.
property features are :  townhome to have a swimming pool in the backyard and a bigger kitchen. 
Return this as search_property_features in the JSON output.

The address component may or may not have all the street, city , state or zipcode portion. Extract whatever is available.
If the property type is not mentioned, default the value as "Single Family Residence".
If the property type is mentioned anything like house or single family or residence, then emit the value as "Single Family Residence".
If the property type is mentioned anything close to town home or townhouse etc, then emit the value as "Townhouse".
If the property type is mentioned anything close to multi family or duplex or multiple family, then emit the value as "Multi Family".
If the property type is mentioned anything like Condomonium or Condo or condos etc, then emit the value as "Condos".
If the property type value is not determinable always default the value as "Single Family Residence".

The radius component may be expressed in miles or in kilometers. Output should in the format like 5mi or 5km depending upon the unit of measure used - miles or kilometers. If no radius component is found, default it to 6mi.
If property features are not found, return it as 'at least 1 bedroom'.
Return these entities in a JSON output format as a python JSON variable I can use. Do not output any other verbose.

Here is the user’s question: <question> {question} </question>

How do you respond to the user’s question?
Think about your answer first before you respond. Give your response in JSON format and exclude any other additional verbose.
Assistant:
"""

# Here we will use Anthropic Claude LLM to do the extraction of the following entities from the user prompt:
# - address
# - property type
# - radius within which the customer is looking for a property
# - additional property features that the customer is looking for (optional)
def extract_entities(question):
    prompt_template = PromptTemplate(template=user_prompt_template, input_variables=["question"])
    prompt = prompt_template.format (question=question)

    request_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 3000,
        "temperature": 0.7,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    })


    accept = 'application/json'
    contentType = 'application/json'
    extracted_entities = {}
    

    try:
        response = bedrock_client.invoke_model(
            modelId=modelId,
            body=request_body
        )

        response_body = json.loads(response['body'].read())
        extracted_entities = response_body['content'][0]['text']
        print(extracted_entities) 
    except botocore.exceptions.ClientError as error:

        if error.response["Error"]["Code"] == "AccessDeniedException":
            print(
                f"\x1b[41m{error.response['Error']['Message']}\
                    \nTo troubeshoot this issue please refer to the following resources.\
                     \nhttps://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html\
                     \nhttps://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html\x1b[0m\n"
            )

        else:
            raise error
    return extracted_entities


# Amazon Location Services for Geocoding :
# Here we will leverage Amazon location services for geocoding. Geocoding is the process of converting addresses 
# (like a street address) into geographic coordinates (latitude and longitude), which can be used to place markers 
# on a map or identify locations in spatial data. It helps map a physical location, such as "1600 Pennsylvania Ave NW, Washington, D.C.," 
# into its corresponding geographic coordinates, enabling applications like GPS navigation, location-based services, 
# or geographic information systems (GIS).

def invoke_aws_loc_service(address, index_name='explore.place.Esri'):
    # Initialize the Amazon Location Service client
    location_client = boto3.client('location', region_name='us-east-1')

    if address is None or address == "":
        print("Address is None or empty")
        return None

    try:
        # Call the search_place_index_for_text method
        response = location_client.search_place_index_for_text(
            IndexName=index_name,
            Text=address
        )

        # Extract the first result (assuming it's the most relevant)
        if response['Results']:
            place = response['Results'][0]['Place']
            longitude, latitude = place['Geometry']['Point']
            
            return {
                'address': address,
                'longitude': longitude,
                'latitude': latitude,
                'label': place.get('Label', ''),
                'country': place.get('Country', '')
            }
        else:
            return None

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

# Run Geospatial Hybrid Retrieval Elastic Query:
# Now we will proceed to run a hybrid (keyword + geopspatial) retrieval from elastic search index with 
# geocoded search location coordinates. We will pass that to the elastic query, to search for properties 
# that existing within a distance radius of user prefered location. We will also pass the search property type 
# (like townhome, single family residence etc) to the query so that we find the exact property that the user is looking for.

def run_elastic_geospatial_query (geo_coded_lat, geo_coded_long, search_property_radius,search_property_type,search_property_features,index_name):
    resp = els_client.search(
        index=index_name,
        query={
            "bool": {
                "must": {
                    "match": {
                        "propertyType": {
                           "query": search_property_type,
                           "boost": 1.5
                        }
                    }
                },
                "should": {
                    "semantic": {
                        "field": "propertyFeatures_v",
                        "query": search_property_features,
                        "boost": 3.0,
                    }
                },
                "filter": {
                    "geo_distance" : {
                        "distance": search_property_radius, 
                        "propertyCoordinates": {
                            "lat": geo_coded_lat, 
                            "lon": geo_coded_long
                        }
                    }
                },
            }
        }
    )    
    
    return resp

#Geospatial RAG in action
#The real estate properties data found from Elastic is now passed as an additional context to the LLM 
# via Amazon Bedrock, to perform RAG.
def run_geospatial_rag(question, context):
    user_recommendation_template = """
Human: You will be acting as a Real estate realtor. Your end users will ask questions about finding properties near to a specific location given in the form of an address. This address may sometimes contains the Street number, Street Name, City name, State name and zip code. If the country name is not mentioned, consider it as USA.  

You will answer only based on the context given: <context>{context}</context>
Here are some important rules for the interaction:
- Always stay in character of being a Real estate advisor, trying to help find properties.
- If you are unsure how to respond, say “Sorry, I didn’t understand that. Could you repeat the question?”
- If someone asks something irrelevant, say, “Sorry, I don't know.”

Here is the user’s question: <question> {question} </question>
Go ahead and answer.
Assistant:
    """

    recommendation_template = PromptTemplate(template=user_recommendation_template, input_variables=["context", "question"])
    prompt = recommendation_template.format (question=question,context=context)
    
    extracted_entities = {}
    

    request_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 10000,
        "temperature": 0.7,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    })

    try:
        response = bedrock_client.invoke_model(
            modelId=modelId,
            body=request_body
        )
        response_body = json.loads(response['body'].read())    

        if debug:
            print(response_body['content'][0]['text'])
        return response_body['content'][0]['text']


    except botocore.exceptions.ClientError as error:

        if error.response["Error"]["Code"] == "AccessDeniedException":
            print(
                f"\x1b[41m{error.response['Error']['Message']}\
                    \nTo troubeshoot this issue please refer to the following resources.\
                     \nhttps://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html\
                     \nhttps://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html\x1b[0m\n"
            )

        else:
            raise error

# Display the results from Elastic in a readable Tabular form.
# The following utility will display the results from Elastic in a tabular format.

def display_pretty_table(results):
    data = results
    
    # Create a list to store the rows
    table_data = []

    # Add rows to the table data
    for hit in data['hits']['hits']:
        source = hit['_source']
        table_data.append([
            source['propertyId'],
            source['propertyName'],            
            source['propertyAddress'],
            source['propertyType'],
        ])

    # Create a pandas DataFrame
    df = pd.DataFrame(table_data, columns=["ID", "Property Name", "Address", "Type"])

    # Display the table using Streamlit
    st.header("And here comes the greateness of Hybrid Geospatial search from Elastic")
    st.table(df)

# Plotting Real Estate property details on a Map.
# In order to visually show the geographic locations of each property that is found by searching Elastic database, 
# we need to plot these on a Map. The following display_map utility does the same.

def display_map(search_location, data):
    points = []
    
    for hit in data['hits']['hits']:
        source = hit['_source']
        coordinates = source['propertyCoordinates'].split(',')
        latitude = float(coordinates[0])
        longitude = float(coordinates[1])
        new_point = {
            "name": source['propertyId'],
            "tooltip": f"{source['propertyType']} : {source['propertyName']} : {source['propertyAddress']}",
            "latitude": latitude,
            "longitude": longitude
        }
        points.append(new_point)

    if not points:
        st.write("Currently no properties found. Please check back with us. We are continuously adding newer listings.")
        return

    # Calculate the center point
    center_lat = sum(point['latitude'] for point in points) / len(points)
    center_lon = sum(point['longitude'] for point in points) / len(points)

    # Create a map centered on the mean of all points
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    # Add markers for each point
    for point in points:
        folium.Marker(
            location=[point['latitude'], point['longitude']],
            popup=point['name'],
            tooltip=point['tooltip']
        ).add_to(m)

    # Display the map title
    st.header(f"Real Estate Properties near: {search_location}")

    # Display the map in Streamlit
    folium_static(m)

# Here is the complete flow of getting response from the LLMs.
def get_ai_response(callback, prompt):
    
    # Step 1 : Named Entitiy Extraction: Get the address, radius, property features from the search.
    extracted_entities_JSON = json.loads(extract_entities(prompt))
    search_property_type = extracted_entities_JSON["search_property_type"]
    search_property_address = extracted_entities_JSON["search_property_address"]
    search_property_radius = extracted_entities_JSON["search_property_radius"]
    search_property_features = extracted_entities_JSON["search_property_features"]

    ner_data = {
        'Search Property Type': [search_property_type],
        'Search Property Address': [search_property_address],
        'Search Property Distance': [search_property_radius],
        'Search Property Features': [search_property_features]
    }
    df = pd.DataFrame(ner_data)
    with st.expander("Named Entity Recognition (NER) at work.."):
        #st.header("Named Entity Recognition (NER) at work")
        st.table(df)
    
    ##
    # Step 2 : Geocoding using AWS Location Services. Using the address information, geocode and get longitude and latitude.
    aws_location_service_result = invoke_aws_loc_service(search_property_address)
    if (debug):
        print(aws_location_service_result)
        print(type(aws_location_service_result))

    geo_coded_long = aws_location_service_result["longitude"]
    geo_coded_lat = aws_location_service_result["latitude"]
    geo_coded_add = aws_location_service_result["address"]
    
    if (debug):
        print(f'And here is geocoded long for search address: {geo_coded_long}')
        print(f'And here is geocoded lat for search address: {geo_coded_lat}')
        print(f'And here is geocoded address for search address: {geo_coded_add}')
    
    geo_coded_data = {
        'Geo coded Address': [geo_coded_add],
        'Geo coded Latitude': [geo_coded_lat],
        'Geo coded Longitude': [geo_coded_long]
    }
    df = pd.DataFrame(geo_coded_data)
    #st.header("Geocoding using Amazon Location Services at work")
    with st.expander("Geocoding using Amazon Location Services at work.."):
        st.table(df)
    placeholder = st.empty()
    placeholder.subheader(" Almost there : Elastic + Amazon Bedrock LLMs are at work...")

    # Step 3: Using the address coordinates and the radius, perform an Elastic search operation to find the nearest points of interest
    results = run_elastic_geospatial_query (geo_coded_lat, geo_coded_long, search_property_radius, search_property_type,search_property_features, index_name)
    data = results.body
    if debug:
        print("***** Elastic Search Results - start")
        print(results.body)
        print("***** Elastic Search Results - end")
    
    results_found = False
    
    for hit in data['hits']['hits']:
        source = hit['_source']
        results_found = True
    
    if results_found is False:
        Title = "<h2>Currently no properties found. Please check back with us. We are continuosly adding newer listings.</h2>"
        st.header(Title)
        return
    
    # Step 4: Run Geo Spatial RAG    
    rag_summary = run_geospatial_rag(prompt, results.body)    

    # Step 5: Display results in a Tabular form
    display_pretty_table(results.body)

    # Step 6: Now plot the top 3 relevant search results on a Map.
    display_map(search_property_address, results.body)

    response = rag_summary
    placeholder.empty()
    return f"AI response to: {response}"

def main():
    st.title("Hybrid Geo Spatial RAG using Elastic and Amazon Bedrock")
    st.image("elastic-aws-logo.png", width=600)
    intro_text = """
    In this streamlit application you will see how to use Elastic search, Amazon Bedrock, Anthropic Claude 3 
    and Langchain to build a Retrieval Augmented Generation (RAG) solution that leverages Geospatial features of Elastic.
    """
    usecase_text = """
    This application introduces an interactive AI agent designed to assist with real estate inquiries. 
    Users looking to purchase properties, such as townhomes, condos, or single-family homes, 
    in specific locations (e.g., New York, NY or Cupertino, CA) can use the agent to find listings 
    that match their preferences. These preferences can include factors like city, distance, property type, 
    and desired amenities such as a swimming pool or lawn.
    """
    with st.expander("About"):
        st.subheader("Introduction")
        st.markdown(intro_text)
        st.subheader("Use case")
        st.markdown(usecase_text)
        st.subheader("Geo Spatial RAG Architecture")
        st.image("geo-spatial-RAG-architecture.svg")
        st.subheader("Elastic endpoints Info")
        st.write(els_client.info())
        st.write("INFO: Successfully connected to Elastic endpoints")
        st.subheader("Power of Hybrid Search : Lexicographical + Geospatial + Vector Similarity")
        st.markdown(
            """
            ```Python
            resp = els_client.search(
                    index=index_name,
                    query={
                        "bool": {
                            "must": {
                                "match": {
                                    "propertyType": {
                                    "query": search_property_type,
                                    "boost": 1.5
                                    }
                                }
                            },
                            "should": {
                                "semantic": {
                                    "field": "propertyFeatures_v",
                                    "query": search_property_features,
                                    "boost": 3.0,
                                }
                            },
                            "filter": {
                                "geo_distance" : {
                                    "distance": search_property_radius, 
                                    "propertyCoordinates": {
                                        "lat": geo_coded_lat, 
                                        "lon": geo_coded_long
                                    }
                                }
                            },
                        }
                    }
                ) 
            ```   
            """
        )


    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    with st.expander("Example Prompts to try:"):
        st.markdown("- Find me a Town house in Frisco, TX within 5 miles distance. I prefer that the townhoume has a jack and jill baths upstairs.")
        st.markdown("- Find townhomes near Apple campus in California.")
        st.markdown("- Find me luxury condos in Cupertino, CA within 15 miles distance that has a private balcony and that is just near to Apple campus. I would like spa or sauna along with clubhouse facilities. An outdoor pools is even great. However, I want HOA fees per year not to exceed $10K.")
        st.markdown("- Find me some multi family residences near to Cupertino california. I prefer a private backyard. I would like the property to be near to malls, schools, tech giant companies. I do not want annual tax assessment amoutn to exceed $10K.")
        st.markdown("- Find me a single family residence near Frisco, TX. I like the home to feature high ceilings. I prefer the second bedroom downstairs for my elderly parents. I like backyard fenced with stone and wood. I prefer flooring that has mix of carpet, ceramic tiles and hardwood. Keep my HOA expenses under $1000 annually.")

    if prompt := st.chat_input("What does your dream house looks like?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Create a new placeholder for bot response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            # Simulate typing
            message_placeholder.markdown("Bot is about to unleash the power of Elastic's Hybrid Geospatial RAG with Amazon Bedrock...")

            # Execute the database query
            try:
                result = get_ai_response(progress_callback, prompt)
                # Split the result into lines
                lines = result.split('\n')
                for line in lines:
                    full_response += line + '\n'
                    # Use regex to detect list items and preserve their formatting
                    formatted_response = re.sub(r'^(\d+\.|\*)\s', r'&nbsp;&nbsp;&nbsp;&nbsp;\1 ', full_response, flags=re.MULTILINE)
                    # Replace newlines with <br> for proper line breaks in markdown
                    #formatted_response = formatted_response.replace('\n', '<br>')
                    message_placeholder.markdown(formatted_response + "▌", unsafe_allow_html=True)
                    time.sleep(0.1)

                message_placeholder.markdown(formatted_response, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": formatted_response})

            except Exception as e:
                error_message = f"Unable to find what you are looking for. Please Retry a different question. Truly apologize for the inconvinience caused. ERROR: {str(e)}"
                message_placeholder.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

def progress_callback(progress):
    # This function will be called by the database query to update progress
    st.session_state.progress = progress
    

if __name__ == "__main__":
    main()
